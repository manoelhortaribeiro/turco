from setuptools import setup

setup(name='turco',
      version='0.1',
      description='easy to use library that automates a bunch of stuff in Amazon mechanical turk ',
      url='http://github.com/manoelhortaribeiro/turco',
      author='Manoel Horta Ribeiro',
      author_email='manoelhortaribeiro@gmail.com',
      license='MIT',
      packages=['turco'],
      zip_safe=False,
      include_package_data=True,
      entry_points = {
            'console_scripts': ['turco-init=turco.command_line:init',
                                'turco-create-questions=turco.command_line:create_questions',
                                'turco-publish-questions=turco.command_line:publish_questions',
                                'turco-retrieve-questions=turco.command_line:retrieve_questions'
                                ]
            }
      )