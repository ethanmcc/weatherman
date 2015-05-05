# weatherman.py

`weatherman` is a script that wraps the creation of Elastic Beanstalk stacks
via CloudFormation. It generates a template based on input and configuration,
then passes it on to AWS using
[CloudFormationConnection.create_stack](http://boto.readthedocs.org/en/latest/ref/cloudformation.html#boto.cloudformation.connection.CloudFormationConnection.create_stack).

## Signature

The script has usage as follows:

	usage: weatherman.py [-h] [-c CONFIG_PATH] [-e ENV] [--dry-run]
	                     [--db-engine DB_ENGINE]
	                     [--db-engine-version DB_ENGINE_VERSION] [--tags TAGS]
	                     [--tag-only] [-n NOTIFICATION_EMAIL] [-s STACK_VERSION]
	                     [--stack-type]
	                     [-p]
	                     app-name
	                     
#### app-name
Name of Elastic Beanstalk application to create an environment in. The
application will be created if it doesn't exist.
	
## Options

Command line options will override corresponding config file values when
supplied.

#### -h, --help
show this help message and exit
	
#### -c CONFIG_PATH, --config-path CONFIG_PATH
Path to weatherman config file. Defaults to `'~/.weathermanrc'`. Options are
described [here](#configuration).

#### -e ENV, --env ENV
Environment (test, dev, qa, pt, prod). Defaults to 'dev'

#### --dry-run
If this option is passed, weatherman prints the relevant CloudFormation JSON
and then exits.

#### --db-engine DB_ENGINE
If CloudFormation's API ever supports it, this adds JSON that will create an
RDS database associated with the Elastic Beanstalk stack.

#### --db-engine-version DB_ENGINE_VERSION
If CloudFormation's API ever supports it, this will set the version of the RDS
database associated with the Elastic Beanstalk stack.

#### --tags TAGS
A list of tags to place on the instance (e.g. vnoc-rsg) in the format
`TAG1NAME=value,TAG2NAME=value2`
	  	  
#### --tag-only
If this option is passed, weatherman will add environment tags and any tags
passed with `--tags` to an existing stack and then exit.

#### -n NOTIFICATION_EMAIL, --notification-email NOTIFICATION_EMAIL
Specify the notification email to receive updates on the Elastic Beanstalk
stack.

#### -s STACK_VERSION, --stack-version STACK_VERSION
A stack version of `2` would create a stack named something like
`appname-envname2` or `myapp-dev2`. This feature could be useful for swapping
stacks in a blue-green deploy scenario.

#### -p, --prompt-db-password
Environments labeled `prod` will automatically prompt for password. Otherwise,
the username and password will just be the app, environment and stack version
mashed together.

#### --stack-type
Optional key for stack solution type.  `python34` is the default, currently 
`nodejs` is the only other option

## Configuration

Weatherman accepts a configuration file to specify default and 
environment-specific options.

Here's a sample config file, which wants to default to `~/.weathermanrc`:

	[DEFAULT]
	notification_email = paulbunyan@example.com
	iam_profile = my.favorite.profile
	instance_type = t2.micro
	assign_public_ip = false
	assign_elb_public_ip = false
	db_instance_class = db.t1.micro
	
	[test]
	vpc_id = vpc-4f4f4f4f
	public_subnets = subnet-f5f5f5f5,subnet-a5a5a5a5
	private_subnets = subnet-d2d2d2d2,subnet-b2b2b2b2
	ec2_keyname = myec2keyname
	
	[dev]
	vpc_id = vpc-3c3c3c3c
	public_subnets = subnet-f4f4f4f4,subnet-b5b5b5b5
	private_subnets = subnet-e2e2e2e2,subnet-a2a2a2a2
	ec2_keyname = anotherec2keyname
	instance_type = m3.medium

#### vpc_id

Specify the id of the VPC for the stack.

#### public_subnets

Specify the public subnets, separated by commas (e.g.
`subnet-345345,subnet-123123`).

#### private_subnets

Specify the private subnets, separated by commas (e.g.
`subnet-345345,subnet-123123`).

#### ec2_keyname

Specify an EC2 keyname to use.

#### instance_type

Specify the instance type for your instance (e.g. `m3.medium`).

#### notification_email

Specify the notification email to receive updates on the Elastic Beanstalk
stack.

#### iam_profile

Specify the IAM profile to associate with the Elastic Beanstalk instances.

#### assign_public_ip

If `true`, instances will use public IP addresses.

#### assign_elb_public_ip

If `true`, the Elastic Load Balancer will use a public IP address.

#### db_instance_class

Specify the database instance class (e.g. `db.t1.micro`). This won't work
until AWS updates the CloudFormation API to actually create Elastic Beanstalk
instances.
