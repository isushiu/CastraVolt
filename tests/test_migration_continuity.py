from alembic.config import Config
from alembic.script import ScriptDirectory


def test_existing_adoption_revision_is_in_single_upgrade_chain():
    scripts=ScriptDirectory.from_config(Config('alembic.ini'))
    previous=scripts.get_revision('0007_optional_adoption')
    assert previous.down_revision=='0006_prediction_idempotency'
    head=scripts.get_revision(scripts.get_current_head())
    assert head.down_revision==previous.revision


from test_accounts import account_settings


def test_upgrade_from_existing_adoption_revision_preserves_prediction_history(account_settings):
    import os,subprocess,sys
    from sqlalchemy import create_engine,text
    from sqlalchemy.orm import Session
    from castravolt.account_models import User
    from castravolt.project_models import Project,Site,Prediction
    from castravolt.auth import now
    engine=create_engine(account_settings.database_url)
    def migrate(target,command='upgrade'):
        run=subprocess.run([sys.executable,'-m','alembic',command,target],env={**os.environ,'CASTRAVOLT_DATABASE_URL':account_settings.database_url},capture_output=True,text=True)
        assert run.returncode==0,run.stderr
    try:
        migrate('0006_prediction_idempotency','downgrade')
        with Session(engine) as db:
            user=User(name='Migration fixture',email='migration@example.com',password_hash='fixture-not-a-login',created_at=now(),verified_at=now());db.add(user);db.flush()
            project=Project(owner_id=user.id,name='Preserved project',description='',created_at=now(),updated_at=now());db.add(project);db.flush()
            site=Site(project_id=project.id,name='Preserved site',latitude=3.1,longitude=101.6,state='SELANGOR',category='Office',address='',created_at=now(),updated_at=now());db.add(site);db.flush()
            prediction=Prediction(site_id=site.id,requester_id=user.id,input_snapshot={'legacy':'preserve'},raw_estimate=4.4,displayed_total=4,model_version='legacy',extraction_rule_version='legacy',poi_timestamp=now(),adoption_reference_year=2025,adoption_value=560,rounding_policy='nearest_half_up_minimum_1',idempotency_key='fixture',created_at=now());db.add(prediction);db.commit();pid=prediction.id
        migrate('0007_optional_adoption')
        migrate('head');migrate('head')
        with Session(engine) as db:
            saved=db.get(Prediction,pid)
            assert saved.input_snapshot=={'legacy':'preserve'} and saved.adoption_value==560 and saved.displayed_total==4
            assert db.scalar(text('SELECT COUNT(*) FROM registration_months'))==66
            assert db.scalar(text('SELECT SUM(count) FROM registration_months'))==6401
            assert db.scalar(text("SELECT version_num FROM alembic_version"))=='0008_registration_trends'
            assert db.scalar(text("SELECT is_nullable FROM information_schema.columns WHERE table_name='predictions' AND column_name='adoption_value'"))=='YES'
    finally:engine.dispose()
