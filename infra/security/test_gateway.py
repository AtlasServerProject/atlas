import hashlib,hmac,importlib.util,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from gateway_identity import envelope
class IdentityTest(unittest.TestCase):
 def test_canonical_ip_and_signature(self):
  key=b'synthetic-private-gateway-key-01234567890123456789'
  result=envelope('POST','/api/v1/auth/login','2001:0db8::1',key,1792929600)
  self.assertEqual(result['X-Atlas-Verified-IP'],'2001:db8::1')
  payload=b'POST\n/api/v1/auth/login\n1792929600\n2001:db8::1'
  self.assertEqual(result['X-Atlas-IP-Signature'],hmac.new(key,payload,hashlib.sha256).hexdigest())
 def test_rejects_missing_identity_hostnames_and_weak_keys(self):
  for ip in [None,'localhost','example.invalid','127.0.0.1, 203.0.113.1','1.2.3.999']:
   with self.assertRaises(ValueError):envelope('GET','/',ip,b'x'*48,1792929600)
  with self.assertRaises(ValueError):envelope('GET','/','127.0.0.1',b'short',1792929600)
if __name__=='__main__':unittest.main()
