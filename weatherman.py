try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
from getpass import getpass
import logging
import os.path
import sys
import time

from troposphere import Ref, Template, Output, GetAtt, Join
import argh
import boto
import troposphere.ec2 as ec2
import troposphere.elasticbeanstalk as eb


logger = logging.getLogger('weatherman')


def get_config(path='~/.weathermanrc', env='dev', defaults=None):
    if defaults is None:
        defaults = {}
    defaults['env'] = env
    config = ConfigParser(defaults=defaults)
    config.read(os.path.expanduser(path))
    return config[env]


def build_security_group(app, config):
    sg = ec2.SecurityGroup('SecurityGroup')
    sg.GroupDescription = 'Security Group for {0}'.format(app.stackname)
    sg.SecurityGroupIngress = [
        {
            "IpProtocol": "tcp",
            "FromPort": "80",
            "ToPort": "80",
            "CidrIp": "10.0.0.0/8"
        },
        {
            "IpProtocol": "tcp",
            "FromPort": "80",
            "ToPort": "80",
            "CidrIp": "192.168.0.0/16"
        },
    ]
    sg.VpcId = config.get('vpc_id')
    return sg


def build_eb_configuration_template(app, config):
    ct = eb.ConfigurationTemplate('ConfigurationTemplate')
    ct.ApplicationName = app.name
    ct.SolutionStackName = ('64bit Debian jessie v1.1.0 running '
                            'Python 3.4 (Preconfigured - Docker)')
    ct.OptionSettings = [
        eb.OptionSettings(
            Namespace='aws:autoscaling:launchconfiguration',
            OptionName='IamInstanceProfile',
            Value=config.get('iam_profile'),
        ),
        eb.OptionSettings(
            Namespace='aws:autoscaling:launchconfiguration',
            OptionName='EC2KeyName',
            Value=config.get('ec2_keyname'),
        ),
        eb.OptionSettings(
            Namespace='aws:autoscaling:launchconfiguration',
            OptionName='InstanceType',
            Value=config.get('instance_type'),
        ),
        eb.OptionSettings(
            Namespace='aws:autoscaling:launchconfiguration',
            OptionName='SecurityGroups',
            Value=Ref('SecurityGroup'),
        ),
        eb.OptionSettings(
            Namespace='aws:elasticbeanstalk:sns:topics',
            OptionName='Notification Endpoint',
            Value=config.get('notification_email'),
        ),
        eb.OptionSettings(
            Namespace='aws:ec2:vpc',
            OptionName='VPCId',
            Value=config.get('vpc_id'),
        ),
        eb.OptionSettings(
            Namespace='aws:ec2:vpc',
            OptionName='Subnets',
            Value=config.get('private_subnets'),
        ),
        eb.OptionSettings(
            Namespace='aws:ec2:vpc',
            OptionName='AssociatePublicIpAddress',
            Value=config.get('assign_public_ip'),
        ),
        eb.OptionSettings(
            Namespace='aws:ec2:vpc',
            OptionName='ELBSubnets',
            Value=config.get('public_subnets'),
        ),
    ]
    if not config.getboolean('assign_elb_public_ip'):
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:ec2:vpc',
            OptionName='ELBScheme',
            Value='internal',
        ))
    db_engine = config.get('db_engine')
    if db_engine:
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:rds:dbinstance',
            OptionName='DBUser',
            Value=''.join([app.name, app.env]),
        ))
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:rds:dbinstance',
            OptionName='DBInstanceClass',
            Value=config.get('db_instance_class'),
        ))
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:rds:dbinstance',
            OptionName='DBAllocatedStorage',
            Value='5',
        ))
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:rds:dbinstance',
            OptionName='MultiAZDatabase',
            Value='false',
        ))
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:ec2:vpc',
            OptionName='DBSubnets',
            Value=config.get('private_subnets'),
        ))
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:rds:dbinstance',
            OptionName='DBDeletionPolicy',
            Value='Snapshot',
        ))
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:rds:dbinstance',
            OptionName='DBEngine',
            Value=db_engine,
        ))

        db_password = ''.join([app.name, app.env])
        if app.env == 'prod' or config.get('prompt_db_password'):
            db_password = getpass('Enter database password: ')
        ct.OptionSettings.append(eb.OptionSettings(
            Namespace='aws:rds:dbinstance',
            OptionName='DBPassword',
            Value=db_password,
        ))

        db_engine_version = config.get('db_engine_version')
        if db_engine_version:
            ct.OptionSettings.append(eb.OptionSettings(
                Namespace='aws:rds:dbinstance',
                OptionName='DBEngineVersion',
                Value=db_engine_version,
            ))
    return ct


def build_eb_environment(app, config):
    env = eb.Environment('Environment')
    env.ApplicationName = app.name
    env.EnvironmentName = app.stackname
    env.TemplateName = Ref('ConfigurationTemplate')
    return env


def build_eb_application_version(app, config):
    version = eb.ApplicationVersion('ApplicationVersion')
    version.ApplicationName = app.name
    version.SourceBundle = eb.SourceBundle(
        'SourceBundle',
        S3Bucket='elasticbeanstalk-samples-us-east-1',
        S3Key='python-sample.zip',
    )
    return version


def build_environment_json(app, config):
    template = Template()
    template.add_resource(build_security_group(app, config))
    template.add_resource(build_eb_configuration_template(app, config))
    template.add_resource(build_eb_environment(app, config))
    template.add_resource(build_eb_application_version(app, config))
    template.add_output(Output(
        'WebsiteURL',
        Value=Join('', ['http', GetAtt('Environment', 'EndpointURL')]),
    ))
    return template


def ensure_application(app):
    beanstalk = boto.connect_beanstalk()
    try:
        logger.info('Creating application %s.', app.name)
        beanstalk.create_application(app.name)
    except boto.exception.BotoServerError as exc:
        if 'already exists' not in exc.message:
            raise
        else:
            logger.info('Application %s already exists.', app.name)


def launch_stack(app, template):
    cf = boto.connect_cloudformation()
    try:
        cf.create_stack(stack_name=app.stackname,
                        template_body=template.to_json())
    except boto.exception.BotoServerError as exc:
        logger.error('Error creating stack: %s', exc.message)
        sys.exit(1)


def wait_for_stack(stackname):
    cf = boto.connect_cloudformation()
    logger.info('Waiting for stack creation for %s to complete.', stackname)
    while True:
        desc = cf.describe_stacks(stackname)[0]
        if desc.stack_status != 'CREATE_IN_PROGRESS':
            break
        time.sleep(1)
    if desc.stack_status != 'CREATE_COMPLETE':
        logger.error('Error creating stack. Status: %s', desc.stack_status)


def apply_instance_tags(app, tags=None):
    instance_tags = {'environment': app.env}
    if tags:
        for tag in tags.split(','):
            key, value = tag.split('=', 1)
            instance_tags[key] = value

    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(
        filters={'tag:elasticbeanstalk:environment-name': app.stackname})
    instances = [i for r in reservations for i in r.instances]
    for instance in instances:
        for tag, value in instance_tags.items():
            instance.add_tag(tag, value)


class App(object):
    def __init__(self, name, env, stack_version):
        self.name = name
        self.env = env
        self.stackname = '{}-{}{}'.format(name, env, stack_version)


def tag(app_name, env='dev', stack_version='', tags=None):
    app = App(app_name, env, stack_version)
    apply_instance_tags(app, tags=tags)


def main(app_name, config_path='~/.weathermanrc', env='dev', dry_run=False,
         db_engine=None, db_engine_version=None, tags=None,
         notification_email=None, stack_version='', prompt_db_password=False):
    app = App(app_name, env, stack_version)
    config = get_config(config_path, env)
    if db_engine:
        config['db_engine'] = db_engine
    if notification_email:
        config['notification_email'] = notification_email
    if db_engine_version:
        config['db_engine_version'] = db_engine_version
    if prompt_db_password:
        config['prompt_db_password'] = 'true'
    template = build_environment_json(app, config)
    if dry_run:
        print(template.to_json())
    else:
        ensure_application(app)
        launch_stack(app, template)
        wait_for_stack(app.stackname)
        apply_instance_tags(app, tags)


argh.dispatch_command(main)
