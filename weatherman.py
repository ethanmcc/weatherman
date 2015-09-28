try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
from subprocess import Popen, list2cmdline
import argparse
import os


STACK_TYPE_MAP = {
    'python34': '64bit Amazon Linux 2015.03 v1.3.1 running Python 3.4',
    'python34_2': '64bit Amazon Linux 2015.03 v2.0.1 running Python 3.4',
    'python34docker': '64bit Debian jessie v1.1.0 running '
                'Python 3.4 (Preconfigured - Docker)',
    'nodejs': '64bit Amazon Linux 2015.03 v1.3.1 running Node.js',
}


def build_eb_cli_command(app, config, passthrough_args):
    ebargs = [
        'eb',
        'create',
        app.stackname,
        '--platform={}'.format(app.platform),
        '--debug',
    ] + passthrough_args
    if 'iam_profile' in config:
        ebargs.append(
            '--instance_profile={}'.format(config.get('iam_profile')))
    if 'ec2_keyname' in config:
        ebargs.append('--keyname={}'.format(config.get('ec2_keyname')))
    if 'instance_type' in config:
        ebargs.append('--instance_type={}'.format(config.get('instance_type')))
    if config.get('profile'):
        ebargs.append('--profile={}'.format(config.get('profile')))

    if 'vpc_id' in config:
        ebargs.append('--vpc.id={}'.format(config.get('vpc_id')))
        if config.get('elb_subnets'):
            ebargs.append(
                '--vpc.elbsubnets={}'.format(config.get('elb_subnets')))
        if config.get('assign_elb_public_ip'):
            ebargs.append('--vpc.elbpublic')
            if 'public_subnets' in config:
                if app.env == 'prod':
                    ebargs.append(
                        '--vpc.ec2subnets={}'.format(config.get('public_subnets')))
                    ebargs.append('--vpc.publicip')
                elif 'private_subnets' in config:
                    ebargs.append('--vpc.ec2subnets={}'.format(
                        config.get('private_subnets')))
        elif 'private_subnets' in config:
            ebargs.append('--vpc.ec2subnets={}'.format(
                config.get('private_subnets')))
        if config.get('assign_public_ip'):
            ebargs.append('--vpc.publicip')

    if set(['-db', '--database']).intersection(set(passthrough_args)):
        ebargs.append(
            '--database.username={}'.format(''.join([app.name, app.env])))
        if config.get('db_instance_class'):
            ebargs.append(
                '--database.instance={}'.format(
                    config.get('db_instance_class')))
        if app.env != 'prod' and not config.get('prompt_db_password'):
            ebargs.append(
                '--database.password={}'.format(''.join([app.name, app.env])))
        if config.get('db_engine'):
            ebargs.append(
                '--database.engine={}'.format(
                    config.get('db_engine')))
        if config.get('db_version'):
            ebargs.append(
                '--database.version={}'.format(
                    config.get('db_version')))
        if config.get('db_size'):
            ebargs.append(
                '--database.size={}'.format(
                    config.get('db_size')))
    return ebargs


def init_eb_environment(app):
    print('Creating application {}.'.format(app.name))
    process = Popen([
        'eb', 'init',
        app.name,
        '--platform', app.platform,
        '--region', app.region,
    ])
    process.wait()


class App(object):
    def __init__(self, name, env, stack_version, platform):
        self.name = name
        self.env = env
        if env == 'prod':
            self.stackname = '{}{}'.format(name, stack_version)
        else:
            self.stackname = '{}-{}{}'.format(name, env, stack_version)
        self.platform = platform

        # TODO: parse arg
        self.region='us-east-1'


def main(config, passthrough_args=None):
    app = App(
        config.get('appname'),
        config.get('env', 'dev'),
        config.get('stack_version', ''),
        STACK_TYPE_MAP[config.get('stack_type')]
    )
    command = build_eb_cli_command(app, config, passthrough_args)
    if config['dry_run']:
        print(list2cmdline(command))
    else:
        init_eb_environment(app)
        process = Popen(command)
        process.wait()
        editor_env = os.environ.copy()
        editor_env['EDITOR'] = (
            'python -c "'
            'import sys; '
            'file = open(sys.argv[-1], \'r\'); '
            'yaml = file.read(); '
            'file.close(); '
            'updated = yaml.replace(\'Notification Endpoint: null\', '
            '\'Notification Endpoint: {}\'); '
            'file = open(sys.argv[-1], \'w\'); '
            'file.write(updated); '
            'file.close();"'.format(config.get('notification_email')))

        pargs = ['eb', 'config', app.stackname]
        if config.get('profile'):
            pargs += ['--profile', config.get('profile')]
        process = Popen(pargs, env=editor_env)
        process.wait()


def get_parser():
    parser = argparse.ArgumentParser(
        prog='weatherman',
        description='Create an Elastic Beanstalk Environment. Options will be '
        'read from your config_path (default ~/.weathermanrc). Additional '
        'options will be passed through to eb create. See eb create --help '
        'for more information.'
    )
    parser.add_argument('appname', help='Application name')
    parser.add_argument(
        '--config-path',
        default='~/.weathermanrc',
        help='Custom config file path (default is ~/.weathermanrc)',
    )
    parser.add_argument('--env',
                        default='dev',
                        help='Environment to create (dev, qa, pt, prod)')
    parser.add_argument('--stack-version',
                        default='',
                        help='Version identifier (e.g. 2 for dev2)')
    parser.add_argument(
        '--stack-type',
        default='python34_2',
        help='Type of stack to create (currently python34, python34docker, '
        'or nodejs)',
    )
    parser.add_argument(
        '--private-subnets',
        help='Comma-separated list of subnet ids for private instances',
    )
    parser.add_argument(
        '--public-subnets',
        help='Comma-separated list of subnet ids for public instances',
    )
    parser.add_argument(
        '--elb-subnets',
        help='Comma-separated list of subnet ids for Elastic Load Balancers',
    )
    parser.add_argument(
        '--vpc-id',
        help='VPC id for instances',
    )
    parser.add_argument(
        '--instance-type',
        default='t2.micro',
        help='Instance type (t2.micro, m3.medium, etc.)',
    )
    parser.add_argument(
        '--iam-profile',
        help='IAM profile name for EC2 instances',
    )
    parser.add_argument(
        '--ec2-keyname',
        help='SSH key name to associate with instances',
    )
    parser.add_argument(
        '--assign-public-ip',
        action='store_true',
        help='Assign public IP to EC2 instances. Default is False.'
             'Default "false"',
    )
    parser.add_argument(
        '--assign-elb-public-ip',
        action='store_true',
        help='Assign public IP to ELB. Default is False.'
    )
    parser.add_argument(
        '--profile',
        help='Name of AWS config profile to use for AWS commands',
    )
    parser.add_argument(
        '--notification-email',
        help='Email address to send stack updates to (Note: This will fail '
        'if you Ctrl-C out. Use eb config to edit it manually.)',
    )
    parser.add_argument(
        '--prompt-db-password',
        action='store_true',
        help='Prompt for DB password rather than building it from environment '
             'details. Defaults True for prod and false for other envs.'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode. Won\'t run external commands.'
    )
    parser.add_argument(
        '--db-instance-class',
        help='Passed through to eb as --database.instance if --database is '
        'set.',
    )
    parser.add_argument(
        '--db-engine',
        help='Passed through to eb as --database.engine if --database is set.'
    )
    parser.add_argument(
        '--db-size',
        help='Passed through to eb as --database.size if --database is set.'
    )
    parser.add_argument(
        '--db-version',
        help='Passed through to eb as --database.version if --database is set.'
    )
    return parser


def dispatch():
    parser = get_parser()
    argsns, passthrough_args = parser.parse_known_args()
    args = vars(argsns)
    config_path = os.path.expanduser(args.get('config_path'))
    config = ConfigParser()
    config.read(config_path)

    args.update(dict(config.items(args['env'])))
    cli_args = []
    for key, value in args.items():
        if value in (False, None):
            continue
        elif key == 'appname':
            cli_args.append(value)
        else:
            cli_args.append('--{}'.format(key.replace('_', '-')))
            if value is not True:
                cli_args.append(value)
    main_args = vars(parser.parse_known_args(cli_args)[0])
    main(main_args, passthrough_args=passthrough_args)


if __name__ == '__main__':
    dispatch()
