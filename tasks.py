import os
import invoke
from invoke import run, task, env, config
from invoke.util import cd, contextmanager

from dotenv import load_dotenv

load_dotenv('.env')

from dotenv import load_dotenv
load_dotenv('.env')

os.environ.setdefault('foo', 'sdgsdg')

conf = config.Config()
conf.load_files()
conf.from_data({'foo': 'secret_key'})
conf.load_shell_env()
conf.merge()

ctx = invoke.Context(config=conf)

@task
def testX(ctx=ctx):
  ctx.run('echo $BITX_KEY')
  print(ctx.config)

@task
def test(context):
    print(context.config)
    print(context.config)
