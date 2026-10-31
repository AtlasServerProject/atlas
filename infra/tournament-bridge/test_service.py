import copy
import unittest
import uuid
from datetime import datetime,timezone,timedelta
from challonge import ApiError
from service import Service, Review, marker

class Repo:
    def __init__(self,n=16,capacity=16):
        self.event={'id':uuid.uuid4(),'slug':'testslug','remote_id':'123','state':'FULL' if n==capacity else 'OPEN','revision':n,'capacity':capacity,'title':'Torneio OU GEN 9','registration_deadline':datetime.now(timezone.utc)+timedelta(minutes=15)}
        self.players=[{'player_uuid':uuid.UUID(int=i+1),'player_name':'Test'+str(i)} for i in range(n)]
        self.finishes=[];self.failures=[];self.valid=True
    def expire(self):
        if self.event['state'] in ('CREATING','OPEN','REVIEW') and self.event['registration_deadline']<=datetime.now(timezone.utc):self.event['state']='CANCELLED'
    def entries(self,id,active=True):return self.players
    def current(self,event):return self.valid
    def finish(self,*args):self.finishes.append(args)
    def fail(self,*args,**kwargs):self.failures.append((args,kwargs))
    def next(self):return self.event if self.event['state'] in ('CREATING','OPEN','FULL') else None

class FakeAPI:
    def __init__(self):self.state='pending';self.people=[];self.fail=False;self.starts=0
    def call(self,method,path,payload=None):
        if '/participants' in path:
            if method=='GET':return {'data':copy.deepcopy(self.people)}
            if method=='POST':
                for attributes in payload['data']['attributes']['participants']:
                    a=attributes.copy();a['seed']=len(self.people)+1
                    self.people.append({'id':str(len(self.people)+1),'attributes':a})
                    if self.fail:self.fail=False;raise TimeoutError() # Remote partially committed, response lost.
                return {'data':self.people}
            if method=='PUT':
                p=next(p for p in self.people if p['id']==path.split('/')[-1].split('.')[0]);p['attributes'].update(payload['data']['attributes']);return {'data':p}
        if '/change_state' in path:self.state='underway';self.starts+=1
        return {'data':{'id':'123','attributes':{'state':self.state}}}

class ServiceTests(unittest.TestCase):
    def test_sixteen_starts_once_replay_safe(self):
        repo=Repo();api=FakeAPI();service=Service(repo,api)
        service.sync(repo.event);service.sync(repo.event)
        self.assertEqual(len(api.people),16);self.assertEqual(api.starts,1)
        self.assertEqual(repo.finishes[-1][2],'STARTED')
        self.assertEqual({p['attributes']['seed'] for p in api.people},set(range(1,17)))
    def test_partial_timeout_reconciles_without_duplicates(self):
        repo=Repo();api=FakeAPI();api.fail=True;service=Service(repo,api)
        service.tick();self.assertTrue(repo.failures)
        service.sync(repo.event)
        self.assertEqual(len(api.people),16);self.assertEqual(api.starts,1)
    def test_fewer_than_sixteen_never_starts(self):
        repo=Repo(15);api=FakeAPI();Service(repo,api).sync(repo.event)
        self.assertEqual(api.starts,0);self.assertEqual(repo.finishes[-1][2],'OPEN')
    def test_foreign_entry_requires_review(self):
        repo=Repo();api=FakeAPI();api.people=[{'id':'external','attributes':{'misc':'foreign','seed':1}}]
        Service(repo,api).tick()
        self.assertTrue(repo.failures[-1][1]['review']);self.assertEqual(api.starts,0)
    def test_cancelled_snapshot_never_starts(self):
        repo=Repo();repo.valid=False;api=FakeAPI();Service(repo,api).sync(repo.event)
        self.assertEqual(api.starts,0);self.assertFalse(repo.finishes)
    def test_eight_starts_at_eight(self):
        repo=Repo(8,8);api=FakeAPI();Service(repo,api).sync(repo.event)
        self.assertEqual(len(api.people),8);self.assertEqual(api.starts,1)
    def test_expired_open_never_calls_api(self):
        repo=Repo(7,8);repo.event['registration_deadline']=datetime.now(timezone.utc)-timedelta(seconds=1)
        api=FakeAPI();Service(repo,api).tick()
        self.assertEqual(repo.event['state'],'CANCELLED');self.assertEqual(api.people,[])
    def test_full_before_deadline_still_starts_after_deadline(self):
        repo=Repo(8,8);repo.event['registration_deadline']=datetime.now(timezone.utc)-timedelta(seconds=1)
        api=FakeAPI();Service(repo,api).tick()
        self.assertEqual(api.starts,1)
    def test_quota_backoff(self):
        repo=Repo()
        class Limited:
            def call(self,*args):raise ApiError(429)
        Service(repo,Limited()).tick()
        self.assertEqual(repo.failures[-1][1]['delay'],86400)

if __name__=='__main__':unittest.main()
