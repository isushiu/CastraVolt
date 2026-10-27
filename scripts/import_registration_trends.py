"""Run after migrations; publish a reviewed aggregate snapshot atomically."""
import argparse,json
from pathlib import Path
from sqlalchemy.orm import Session
from castravolt.config import Settings
from castravolt.database import make_engine
from castravolt.trends import publish_snapshot
from castravolt.trends_data import build_snapshot,packaged_snapshot

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-directory',type=Path);parser.add_argument('--write-package',action='store_true');args=parser.parse_args()
    data=build_snapshot(args.source_directory) if args.source_directory else packaged_snapshot()
    if args.write_package:
        Path('src/castravolt/resources/registration_monthly.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    engine=make_engine(Settings())
    if engine is None:raise SystemExit('Configure the local database first.')
    with Session(engine) as db:publish_snapshot(db,data);db.commit()
    engine.dispose();print(f"Published {data['version'][:12]}: {len(data['months'])} state/month records")
