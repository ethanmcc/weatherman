try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
from subprocess import Popen, list2cmdline
import argparse
import os


STACK_TYPE_MAP = {
    'python34': '64bit Debian jessie v1.1.0 running '
                'Python 3.4 (Preconfigured - Docker)',
    'nodejs': '64bit Amazon Linux 2015.03 v1.3.1 running Node.js',
}


def build_eb_cli_command(app, config, passthrough_args):
    ebargs = [
        'eb',
        'create',
        app.stackname,
        '--instance_profile={}'.format(config.get('iam_profile')),
        '--keyname={}'.format(config.get('ec2_keyname')),
        '--instance_type={}'.format(config.get('instance_type')),
        '--platform={}'.format(app.platform),
        '--vpc.id={}'.format(config.get('vpc_id')),
        '--vpc.ec2subnets={}'.format(config.get('private_subnets')),
    ] + passthrough_args
    # Notification Email
    if config.get('assign_public_ip'):
        ebargs.append('--vpc.publicip')
    if config.get('assign_elb_public_ip'):
        ebargs.append('--vpc.elbpublic')

    if set(['-db', '--database']).intersection(set(passthrough_args)):
        ebargs.append(
            '--database.username={}'.format(''.join([app.name, app.env])))
        if config.get('db_instance_class'):
            ebargs.append(
                '--database.instance={}'.format(
                    config.get('db_instance_class')))
        if not config.get('prompt_db_password'):
            ebargs.append(
                '--database.password={}'.format(''.join([app.name, app.env])))
    return ebargs


def init_eb_environment(app):
    print('Creating application {}.'.format(app.name))
    process = Popen(['eb', 'init', app.name, '--platform', app.platform])
    process.wait()


class App(object):
    def __init__(self, name, env, stack_version, platform):
        self.name = name
        self.env = env
        self.stackname = '{}-{}{}'.format(name, env, stack_version)
        self.platform = platform


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
            'sed -i "s/Notification Endpoint: null/'
            'Notification Endpoint: {}"/g'.format(
                config.get('notification_email')))
        process = Popen(['eb', 'config', app.stackname], env=editor_env)
        process.wait()


def dispatch():
    parser = argparse.ArgumentParser(
        description='Create an Elastic Beanstalk Environment. Options will be '
        'read from your config_path (default ~/.weathermanrc). Additional '
        'options will be passed through to eb create. See eb create --help '
        'for more information.'
    )
    parser.add_argument('appname', help='Application name')
    parser.add_argument(
        '--config-path',
        default=os.path.expanduser('~/.weathermanrc'),
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
        default='python34',
        help='Type of stack to create (currently python34, nodejs)',
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
        '--vpc-id',
        help='VPC id for instances',
    )
    parser.add_argument(
        '--instance-type',
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
        '--db-instance-class',
        help='Instance class to use if a database is specified via --db',
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

    args = vars(parser.parse_known_args()[0])
    config_path = args.get('config_path')
    config = ConfigParser()
    config.read(config_path)

    args.update(config[args['env']])
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
    main_args, passthrough_args = parser.parse_known_args(cli_args)
    main(vars(main_args), passthrough_args=passthrough_args)
