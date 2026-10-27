#!/usr/bin/env python3
"""Read-only public crate snapshot. Uses standard libpq PG* environment/service config.
Never exports player/account data, credentials, balances, keys or opening history.
Run with the operator's psycopg environment. Do not pass credentials on the CLI.
"""
import argparse, datetime, json, pathlib
import psycopg
from psycopg import IsolationLevel

IDENTIFIERS = [f'generation_{i}' for i in range(1,10)] + ['legendary_monthly']

def build_snapshot(connection):
    connection.set_read_only(True)
    connection.set_isolation_level(IsolationLevel.REPEATABLE_READ)
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout='5s'")
        cursor.execute("SELECT c.identifier,c.display_name,r.reward_identifier FROM crates c JOIN crate_rewards r ON r.crate_id=c.id WHERE c.enabled AND c.identifier=ANY(%s) AND r.reward_type='POKEMON' AND r.chance>0 ORDER BY c.identifier,r.id", (IDENTIFIERS,))
        crates={}
        for identifier,name,properties in cursor:
            fields=properties.split();species=fields[0].split(':')[-1]
            if not species.isascii() or not species.isalnum():raise ValueError('Unexpected species identifier')
            crates.setdefault(identifier,{'identifier':identifier,'name':name,'rewards':[]})['rewards'].append({'species':species,'shiny':'shiny=true' in fields})
        cursor.execute('SELECT monthly_period FROM crate_settings WHERE singleton')
        row=cursor.fetchone()
        if len(crates)!=10 or not row or not row[0]:raise ValueError('Incomplete active catalogue')
        return {'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'monthlyPeriod':str(row[0])[:7],'crates':list(crates.values())}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=pathlib.Path);args=parser.parse_args()
    with psycopg.connect(connect_timeout=5) as connection:result=build_snapshot(connection)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    pending=args.output.with_suffix('.pending');pending.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');pending.replace(args.output)
    print('Public catalogue exported:',len(result['crates']),'crates. No private player data.')
if __name__=='__main__':main()
