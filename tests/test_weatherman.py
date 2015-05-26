from unittest import TestCase

import weatherman


class BaseTestCase(TestCase):
    config = {
        'env': 'dev',
        'dry_run': False,
    }
    passthrough_args = []

    @classmethod
    def setUpClass(cls):
        app = weatherman.App(
            'testapp',
            'dev',
            '',
            weatherman.STACK_TYPE_MAP['python34'],
        )
        cls.command = weatherman.build_eb_cli_command(
            app, cls.config, passthrough_args=cls.passthrough_args)


class EmptyConfigurationTestCase(BaseTestCase):

    def test_command_beginning(self):
        self.assertEqual(self.command[:3], ['eb', 'create', 'testapp-dev'])

    def test_command_size(self):
        self.assertEqual(len(self.command), 4)

    def test_exclude_null_values(self):
        for argument in self.command:
            self.assertFalse(argument.endswith('=None'))

    def test_platform(self):
        self.assertIn('--platform=64bit Debian jessie v1.1.0 running Python '
                      '3.4 (Preconfigured - Docker)', self.command)


class PassthroughArgsTestCase(BaseTestCase):
    passthrough_args = [
        'arg1',
        '-arg2',
        '--arg3',
    ]

    def test_args_are_passed_through(self):
        for arg in self.passthrough_args:
            self.assertIn(arg, self.command)


class SampleConfigurationTestCase(BaseTestCase):
    config = {
        'env': 'dev',
        'dry_run': False,
        'iam_profile': 'my.profile',
        'ec2_keyname': 'my.keyname',
        'instance_type': 't2.mine',
        'vpc_id': 'vpcid',
        'private_subnets': 'private1,private2',
    }

    def test_includes_iam_profile(self):
        self.assertIn('--instance_profile=my.profile', self.command)

    def test_includes_ec2_keyname(self):
        self.assertIn('--keyname=my.keyname', self.command)

    def test_includes_instance_type(self):
        self.assertIn('--instance_type=t2.mine', self.command)

    def test_includes_vpc_id(self):
        self.assertIn('--vpc.id=vpcid', self.command)

    def test_includes_private_subnets(self):
        self.assertIn('--vpc.ec2subnets=private1,private2', self.command)


class PublicServerTestCase(BaseTestCase):
    config = {
        'assign_elb_public_ip': True,
        'vpc_id': 'vpcid',
        'public_subnets': 'public1,public2',
    }

    def test_includes_public_subnets(self):
        self.assertIn('--vpc.ec2subnets=public1,public2', self.command)


class DefaultArgumentTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.args = vars(weatherman.get_parser().parse_known_args()[0])

    def test_default_instance_type(self):
        self.assertEqual(self.args['instance_type'], 't2.micro')

    def test_default_platform(self):
        self.assertEqual(self.args['stack_type'], 'python34')

    def test_default_env(self):
        self.assertEqual(self.args['env'], 'dev')

    def test_default_stack_version(self):
        self.assertEqual(self.args['stack_version'], '')
