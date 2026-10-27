from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, AliasChoices, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from castravolt.account_models import User, AccountSession, AccountToken, AuthRateLimit
from castravolt import mail

router = APIRouter(prefix='/api/v1/auth',tags=['Accounts'])
hasher = PasswordHasher(time_cost=2,memory_cost=19456,parallelism=1)
dummy_hash = hasher.hash(secrets.token_urlsafe(32))


def now(): return datetime.now(timezone.utc)
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def names(settings): return ('__Host-castravolt_session','__Host-castravolt_csrf') if settings.secure_cookies else ('castravolt_session','castravolt_csrf')


def database(request: Request):
    if request.app.state.engine is None: raise HTTPException(503,'Account service is unavailable.')
    with Session(request.app.state.engine,expire_on_commit=False) as session:
        yield session


def individual_access(request: Request):
    if request.app.state.settings.internal_access:
        raise HTTPException(404, 'Public account registration and recovery are disabled.')


def current_user(request: Request, db: Session=Depends(database)):
    active=current_session(request,db)
    if not active: raise HTTPException(401,'Please sign in to continue.')
    user=db.get(User,active.user_id)
    if user is None: raise HTTPException(401,'Please sign in to continue.')
    return user


def current_session(request,db):
    value=request.cookies.get(names(request.app.state.settings)[0],'')
    if not value or len(value)>256: return None
    return db.scalar(select(AccountSession).where(AccountSession.token_hash==digest(value),
                     AccountSession.revoked_at.is_(None),AccountSession.expires_at>now()))


def csrf(request: Request,db: Session=Depends(database)):
    settings=request.app.state.settings
    allowed={settings.frontend_url,*settings.cors_origins}
    if request.headers.get('origin') not in allowed: raise HTTPException(403,'This request origin is not allowed.')
    cookie=request.cookies.get(names(settings)[1],'')
    header=request.headers.get('x-csrf-token','')
    if not cookie or len(cookie)>256 or not secrets.compare_digest(cookie,header):
        raise HTTPException(403,'Refresh the page and try again.')
    active=current_session(request,db)
    if active and not secrets.compare_digest(active.csrf_hash,digest(header)):
        raise HTTPException(403,'Refresh the page and try again.')


def throttle(request,db,action,email=''):
    # Committed before credential/token checks so failed attempts still consume quota.
    window=int(now().timestamp())//900
    keys=[f'{action}:ip:{request.client.host if request.client else "unknown"}:{window}']
    if email: keys.append(f'{action}:email:{email}:{window}')
    for key in keys:
        statement=insert(AuthRateLimit).values(key=digest(key),count=1,expires_at=now()+timedelta(minutes=16))
        statement=statement.on_conflict_do_update(index_elements=['key'],set_={'count':AuthRateLimit.count+1}).returning(AuthRateLimit.count)
        count=db.scalar(statement)
        db.commit()
        if count>request.app.state.settings.auth_rate_limit:
            raise HTTPException(429,'Too many attempts. Please try again later.',headers={'Retry-After':'900'})
    db.execute(delete(AuthRateLimit).where(AuthRateLimit.expires_at<now())); db.commit()


def set_cookie(response,settings,name,value,max_age):
    response.set_cookie(name,value,max_age=max_age,secure=settings.secure_cookies,httponly=True,samesite='lax',path='/')


def issue_token(db,user,purpose):
    db.execute(update(AccountToken).where(AccountToken.user_id==user.id,AccountToken.purpose==purpose,
                                        AccountToken.used_at.is_(None)).values(used_at=now()))
    raw=secrets.token_urlsafe(32)
    db.add(AccountToken(user_id=user.id,token_hash=digest(raw),purpose=purpose,
                        expires_at=now()+timedelta(minutes=60 if purpose=='verify' else 30)))
    return raw


def locked_token(db,raw,purpose):
    candidate=db.scalar(select(AccountToken).where(AccountToken.token_hash==digest(raw),AccountToken.purpose==purpose))
    if candidate is None: raise HTTPException(400,'This link is invalid or expired. Request a new one.')
    # All issuance/consumption paths lock user first, then token rows.
    user=db.scalar(select(User).where(User.id==candidate.user_id).with_for_update())
    token=db.scalar(select(AccountToken).where(AccountToken.id==candidate.id,AccountToken.used_at.is_(None),
                    AccountToken.expires_at>now()).with_for_update().execution_options(populate_existing=True))
    if token is None: raise HTTPException(400,'This link is invalid or expired. Request a new one.')
    return user,token


class Credentials(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1,max_length=128)
    @field_validator('email')
    @classmethod
    def normalized(cls,value): return value.casefold()


class Registration(Credentials):
    name: str = Field(min_length=1,max_length=100)
    password: str = Field(min_length=12,max_length=128)
    @field_validator('name')
    @classmethod
    def real_name(cls,value):
        value=value.strip()
        if not value: raise ValueError('Enter your name')
        return value


class LoginInput(BaseModel):
    id: str = Field(min_length=1,max_length=254,validation_alias=AliasChoices('id','email'))
    password: str = Field(min_length=1,max_length=128)


class EmailInput(BaseModel):
    email: EmailStr = Field(max_length=254)
    @field_validator('email')
    @classmethod
    def normalized(cls,value): return value.casefold()


class TokenInput(BaseModel):
    token: str = Field(min_length=20,max_length=256)


class ResetInput(TokenInput):
    password: str = Field(min_length=12,max_length=128)


class Planner(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID
    name: str
    email: str


class AuthResult(BaseModel):
    user: Planner
    csrf_token: str


class CsrfResult(BaseModel):
    csrf_token: str


class Message(BaseModel):
    message: str


@router.get('/csrf',response_model=CsrfResult)
def get_csrf(request: Request,response: Response,db: Session=Depends(database)):
    settings=request.app.state.settings
    active=current_session(request,db)
    value=request.cookies.get(names(settings)[1],'')
    if not value or len(value)>256 or (active and digest(value)!=active.csrf_hash):
        value=secrets.token_urlsafe(32)
        if active: active.csrf_hash=digest(value); db.commit()
        set_cookie(response,settings,names(settings)[1],value,settings.session_hours*3600)
    response.headers['Cache-Control']='no-store'
    return {'csrf_token':value}


@router.post('/register',response_model=Message,status_code=202,dependencies=[Depends(individual_access),Depends(csrf)])
def register(data: Registration,request: Request,background_tasks: BackgroundTasks,db: Session=Depends(database)):
    throttle(request,db,'register',data.email)
    password_hash=hasher.hash(data.password)
    user=db.scalar(select(User).where(User.email==data.email))
    if user is None:
        user=User(name=data.name,email=data.email,password_hash=password_hash,created_at=now())
        try:
            db.add(user); db.flush()
            token=issue_token(db,user,'verify'); db.commit()
        except IntegrityError:
            db.rollback()  # Concurrent duplicate registration has the same public response.
        else:
            background_tasks.add_task(mail.deliver,request.app.state.settings,data.email,'verify-email',token)
    return {'message':'If registration can proceed, a verification email will arrive shortly.'}


@router.post('/verify-email',response_model=Message,dependencies=[Depends(individual_access),Depends(csrf)])
def verify_email(data: TokenInput,request: Request,db: Session=Depends(database)):
    throttle(request,db,'verify')
    user,token=locked_token(db,data.token,'verify')
    user.verified_at=now(); token.used_at=now(); db.commit()
    return {'message':'Email verified. You can now sign in.'}


@router.post('/resend-verification',response_model=Message,status_code=202,dependencies=[Depends(individual_access),Depends(csrf)])
def resend(data: EmailInput,request: Request,background_tasks: BackgroundTasks,db: Session=Depends(database)):
    throttle(request,db,'resend',data.email)
    user=db.scalar(select(User).where(User.email==data.email).with_for_update())
    if user and not user.verified_at:
        token=issue_token(db,user,'verify'); db.commit()
        background_tasks.add_task(mail.deliver,request.app.state.settings,user.email,'verify-email',token)
    return {'message':'If verification is needed, an email will arrive shortly.'}


@router.post('/login',response_model=AuthResult,dependencies=[Depends(csrf)])
def login(data: LoginInput,request: Request,response: Response,db: Session=Depends(database)):
    identifier=data.id.strip().casefold()
    throttle(request,db,'login',identifier)
    if request.app.state.settings.internal_access:
        if identifier!='admin' or not secrets.compare_digest(data.password.encode('utf-8'),b'123'):
            raise HTTPException(401,'Unable to sign in. Check your ID and password.')
        # Insert once; never reset or replace an existing account on a restart.
        from uuid import uuid4
        db.execute(insert(User).values(id=uuid4(),email='admin@castravolt.local',name='Admin',
                   password_hash=hasher.hash('123'),verified_at=now(),created_at=now()).on_conflict_do_nothing(index_elements=['email']))
        identifier='admin@castravolt.local'
    user=db.scalar(select(User).where(User.email==identifier).with_for_update())
    try: valid=hasher.verify(user.password_hash if user else dummy_hash,data.password)
    except (VerificationError,InvalidHashError): valid=False
    if not valid or not user or not user.verified_at:
        raise HTTPException(401,'Unable to sign in. Check your login details.')
    if hasher.check_needs_rehash(user.password_hash): user.password_hash=hasher.hash(data.password)
    old=current_session(request,db)
    if old: old.revoked_at=now()
    raw,csrf_value=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
    settings=request.app.state.settings
    db.add(AccountSession(user_id=user.id,token_hash=digest(raw),csrf_hash=digest(csrf_value),
                         created_at=now(),expires_at=now()+timedelta(hours=settings.session_hours)))
    db.commit()
    for name,value in zip(names(settings),(raw,csrf_value)):
        set_cookie(response,settings,name,value,settings.session_hours*3600)
    return {'user':Planner.model_validate(user),'csrf_token':csrf_value}


@router.get('/me',response_model=Planner)
def me(request: Request,db: Session=Depends(database)):
    active=current_session(request,db)
    if not active: raise HTTPException(401,'Please sign in to continue.')
    return db.get(User,active.user_id)


@router.post('/logout',response_model=Message,dependencies=[Depends(csrf)])
def logout(request: Request,response: Response,db: Session=Depends(database)):
    active=current_session(request,db)
    if active: active.revoked_at=now(); db.commit()
    for name in names(request.app.state.settings): response.delete_cookie(name,path='/',secure=request.app.state.settings.secure_cookies,httponly=True,samesite='lax')
    return {'message':'Signed out.'}


@router.post('/forgot-password',response_model=Message,status_code=202,dependencies=[Depends(individual_access),Depends(csrf)])
def forgot(data: EmailInput,request: Request,background_tasks: BackgroundTasks,db: Session=Depends(database)):
    throttle(request,db,'forgot',data.email)
    user=db.scalar(select(User).where(User.email==data.email).with_for_update())
    if user and user.verified_at:
        token=issue_token(db,user,'reset'); db.commit()
        background_tasks.add_task(mail.deliver,request.app.state.settings,user.email,'reset-password',token)
    return {'message':'If this account is eligible, a password reset email will arrive shortly.'}


@router.post('/reset-password',response_model=Message,dependencies=[Depends(individual_access),Depends(csrf)])
def reset(data: ResetInput,request: Request,db: Session=Depends(database)):
    throttle(request,db,'reset')
    user,token=locked_token(db,data.token,'reset')
    user.password_hash=hasher.hash(data.password)
    token.used_at=now()
    db.execute(update(AccountSession).where(AccountSession.user_id==user.id,AccountSession.revoked_at.is_(None)).values(revoked_at=now()))
    db.execute(update(AccountToken).where(AccountToken.user_id==user.id,AccountToken.purpose=='reset',AccountToken.used_at.is_(None)).values(used_at=now()))
    db.commit()
    return {'message':'Password updated. Sign in with your new password.'}
