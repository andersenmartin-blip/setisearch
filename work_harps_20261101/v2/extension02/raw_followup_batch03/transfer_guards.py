"""Import-safe no-redirect transport and conservative concurrent payload accounting."""
import threading,urllib.request,urllib.error

class PayloadCapError(RuntimeError):pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,request,fp,code,msg,headers,newurl):
  # Returning None delegates to the opener's HTTPError fallback before the redirect body-drain branch.
  return None

def no_redirect_opener():return urllib.request.build_opener(NoRedirect())

def close_http_error(error):
 if isinstance(error,urllib.error.HTTPError):error.close()

class PayloadLedger:
 def __init__(self,cap):
  if not isinstance(cap,int)or cap<=0:raise ValueError('Positive integer cap required')
  self.cap=cap;self.charged=0;self.known=0;self.reserved=0;self.lock=threading.Lock()
 def reserve(self,wanted):
  if wanted<=0:raise ValueError('Positive read allowance required')
  with self.lock:
   allowance=min(wanted,self.cap-self.charged-self.reserved)
   if allowance<=0:raise PayloadCapError('GLOBAL_PAYLOAD_CAP_EXHAUSTED')
   self.reserved+=allowance
   return allowance
 def finish(self,allowance,known_bytes,failed):
  if not 0<=known_bytes<=allowance:raise RuntimeError('Returned bytes exceed read reservation')
  with self.lock:
   if allowance>self.reserved:raise RuntimeError('Reservation accounting mismatch')
   self.reserved-=allowance;self.known+=known_bytes;self.charged+=allowance if failed else known_bytes
   if self.charged+self.reserved>self.cap:raise RuntimeError('Payload budget overflow')
 def snapshot(self):
  with self.lock:return dict(payload_cap_bytes=self.cap,charged_payload_bytes=self.charged,known_returned_payload_bytes=self.known,unknown_bytes_conservatively_charged=self.charged-self.known,reserved_bytes=self.reserved)

def bounded_read(response,wanted,ledger,attempt):
 """Read at most a reservation; failures consume all reserved budget, known or unknown."""
 allowance=ledger.reserve(wanted)
 try:block=response.read(allowance)
 except BaseException as error:
  partial=getattr(error,'partial',b'');known=len(partial)if isinstance(partial,bytes)else 0
  ledger.finish(allowance,known,True);attempt['known_returned_payload_bytes']+=known;attempt['charged_payload_bytes']+=allowance
  raise
 ledger.finish(allowance,len(block),False);attempt['known_returned_payload_bytes']+=len(block);attempt['charged_payload_bytes']+=len(block)
 return block
