#!/usr/bin/env python
"""Generate circle ci config.  """

#pylint: disable=unsubscriptable-object

from pathlib import Path

from update_versions import load_versions

CONFIG_TEMPLATE = '''\
# Code generated by ./scripts/update_config.py, DO NOT EDIT.
version: 2.1
orbs:
  docker-publish: circleci/docker-publish@0.1.6
executors:
  docker: docker-publish/docker
commands:
  publish:
    parameters:
      major:
        type: integer
      minor:
        type: integer
      patch:
        type: integer
      extra_build_args:
        description: >
          Extra flags to pass to docker build. For examples, see
          https://docs.docker.com/engine/reference/commandline/build
        type: string
        default: ''
    steps:
      - checkout
      - setup_remote_docker
      - docker-publish/check
      - docker-publish/build:
          extra_build_args: >-
            <<#parameters.extra_build_args>><<parameters.extra_build_args>><</parameters.extra_build_args>>
            --build-arg NUKE_MAJOR=<< parameters.major >>
            --build-arg NUKE_MINOR=<< parameters.minor >>
            --build-arg NUKE_PATCH=<< parameters.patch >>
          image: natescarlet/nuke
          tag: << parameters.major >>.<< parameters.minor >>v<< parameters.patch >>
      - when:
          condition:
            equal: [ master, << pipeline.git.branch >> ]
          steps:
            - docker-publish/deploy:
                image: natescarlet/nuke
'''


def _get_extra_build_arg_lines(tags):
    if not tags:
        return
    yield f'''\
          extra_build_args: {" ".join([f"--tag natescarlet/nuke:{i}" for i in tags])}
'''


def generate_config():
    """Config generator.  """

    yield CONFIG_TEMPLATE
    yield '''\
jobs:
'''

    jobs = []
    last = None
    for i in load_versions():
        last_extra_tags = []
        if last is None:
            pass
        elif last[0] != i[0]:
            last_extra_tags.append(last[0])
            last_extra_tags.append(f'{last[0]}.{last[1]}')
        elif last[1] != i[1]:
            last_extra_tags.append(f'{last[0]}.{last[1]}')
        yield from _get_extra_build_arg_lines(last_extra_tags)

        jobname = f'publish-{i[0]}-{i[1]}-{i[2]}'
        jobs.append(jobname)
        yield f'''\
  {jobname}:
    filters:
      branches:
        only:
          - master
    executor: docker
    steps:
      - publish:
          major: {i[0]}
          minor: {i[1]}
          patch: {i[2]}
'''
        last = i
    assert last is not None
    yield from _get_extra_build_arg_lines(["latest", last[0], f'{last[0]}.{last[1]}'])

    yield '''\
workflows:
  version: 2
  build and publish:
    jobs:
'''

    for i in jobs:
        yield f'''\
      - {i}
'''


def main():
    config_file = (Path(__file__).parent.parent / '.circleci' / 'config.yml')
    with config_file.open('w', encoding='utf-8') as f:
        for i in generate_config():
            f.write(i)


if __name__ == '__main__':
    main()
