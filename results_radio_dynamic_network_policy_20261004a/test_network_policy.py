import copy
from pathlib import Path
import tempfile
import unittest
import network_policy as n


def fixture(root):
    cert=Path(root)/'certificate';cert.write_bytes(b'fixture certificate\n')
    trust={'path':str(cert),'mode':cert.stat().st_mode&0o777,**n.pin(cert.read_bytes())}
    policy={'schema':'radio-dynamic-loopback-network-policy-v1','proxy_names':list(n.PROXIES),
      'host':'127.0.0.1','http_scheme':'http','all_scheme':'socks5h','port_min':1024,'port_max':65535,
      'no_proxy_pin':n.pin(b'localhost'),'trust_file':trust,'git_exec_path':'/selected/git-core',
      'fixed_environment':dict(n.FIXED),'forbidden_names':['SSL_CERT_DIR','GIT_SSL_CAINFO']}
    source={name:('socks5h' if name.lower()=='all_proxy' else 'http')+'://127.0.0.1:23456' for name in n.PROXIES}
    source.update(NO_PROXY='localhost',no_proxy='localhost',SSL_CERT_FILE=str(cert))
    return policy,source


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.policy,self.source=fixture(self.tmp.name)

    def test_distinct_actual_ports_preserve_one_frozen_policy(self):
        hashes=[]
        for port in (1024,23456,65535):
            source={k:v.replace(':23456',':'+str(port)) for k,v in self.source.items()}
            env,proof=n.build(self.policy,source);hashes.append(proof['proxies']['HTTPS_PROXY']['sha256'])
            self.assertEqual(proof['policy_pin'],n.pin(n.canonical(self.policy)))
            self.assertEqual(proof['proxies']['HTTPS_PROXY']['port'],port)
        self.assertEqual(len(set(hashes)),3)

    def test_remote_localhost_and_ipv6_hosts_are_outside_exact_observed_policy(self):
        for value in ('http://example.com:23456','http://localhost:23456','http://[::1]:23456','http://127.0.0.2:23456'):
            with self.assertRaises(ValueError):n.proxy(value,'http')

    def test_credentials_and_escaped_userinfo_never_appear_in_refusal(self):
        for value in ('http://name:SECRET@127.0.0.1:23456','http://SECRET%40127.0.0.1:23456'):
            with self.assertRaises(ValueError) as e:n.proxy(value,'http')
            self.assertNotIn('SECRET',str(e.exception))

    def test_noncanonical_or_privileged_ports_are_refused(self):
        for port in ('0','80','1023','65536','023456','-1234','23456x'):
            with self.assertRaises(ValueError):n.proxy('http://127.0.0.1:'+port,'http')

    def test_scheme_path_query_fragment_control_and_unicode_are_refused(self):
        for value in ('https://127.0.0.1:23456','http://127.0.0.1:23456/','http://127.0.0.1:23456?a=1',
                      'http://127.0.0.1:23456#x','http://127.0.0.1:23456\n','http://127.0.0.1:２３４５６'):
            with self.assertRaises(ValueError):n.proxy(value,'http')

    def test_absent_proxy_or_case_pair_disagreement_closes(self):
        for change in ('absent','pair','protocol'):
            source=dict(self.source)
            if change=='absent':source.pop('ALL_PROXY')
            elif change=='pair':source['http_proxy']='http://127.0.0.1:34567'
            else:
                for k in ('HTTPS_PROXY','https_proxy'):source[k]='http://127.0.0.1:34567'
            with self.assertRaises(ValueError):n.build(self.policy,source)

    def test_bypass_change_and_extra_trust_configuration_close(self):
        for key,value in (('NO_PROXY','github.com'),('SSL_CERT_DIR','/other'),('GIT_SSL_CAINFO','/other')):
            source={**self.source,key:value}
            with self.assertRaises(ValueError):n.build(self.policy,source)

    def test_trust_file_location_or_bytes_change_closes(self):
        with self.assertRaises(ValueError):n.build(self.policy,{**self.source,'SSL_CERT_FILE':'/elsewhere'})
        Path(self.source['SSL_CERT_FILE']).write_bytes(b'changed')
        with self.assertRaises(ValueError):n.build(self.policy,self.source)

    def test_unrelated_credentials_paths_and_git_commands_are_excluded(self):
        source={**self.source,'PRIVATE_TOKEN':'SECRET','GIT_SSH_COMMAND':'evil','GIT_ASKPASS':'evil',
                'GIT_CONFIG_COUNT':'1','PATH':'/evil','LD_PRELOAD':'/evil'}
        env,proof=n.build(self.policy,source)
        for name in ('PRIVATE_TOKEN','GIT_SSH_COMMAND','GIT_ASKPASS','GIT_CONFIG_COUNT','LD_PRELOAD'):
            self.assertNotIn(name,env);self.assertNotIn(name,proof['actual_environment_names'])
        self.assertEqual(env['PATH'],n.FIXED['PATH']);self.assertNotIn('SECRET',str(proof))

    def test_policy_widening_cannot_be_caller_flag(self):
        for key,value in (('host','example.com'),('port_min',0),('http_scheme','https'),('forbidden_names',[])):
            policy={**self.policy,key:value}
            with self.assertRaises(ValueError):n.build(policy,self.source)


if __name__=='__main__':unittest.main()
