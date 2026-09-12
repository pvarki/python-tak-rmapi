========
takrmapi
========

RASENMAEHER integration API for TAK server

User certificate keys default to EC P-256. Set ``TI_TAK_CERTS_KTYPE=RSA`` in
the container environment to generate RSA user keys instead. Changing this setting
does not rotate existing user keys or change the TAK server's JWT signing identity.

TAK client packages trust the internal CFSSL intermediate and root from
``/ca_public/ca_chain.pem``. Override this path with ``TI_TAK_CA_CHAIN_PATH``
when using a different mount. The chain must include the root CA. HTTPS certificates
and Let's Encrypt roots are not included in the CoT trust bundle.


Docker
------

Production uses ``eclipse-temurin:17-jre-noble`` and Python 3.12. The JDK and
compilers remain in build and development stages for building PyJNIus wheels.
Runtime wheels are installed offline with uv into ``/opt/venv``; neither uv nor
the wheel archives are retained in the production image. ``JAVA_HOME`` points
PyJNIus to the JRE, including ``libjvm.so``. The ``JAVA_RUNTIME_IMAGE`` build
argument accepts a compatible Ubuntu Noble Java 17 runtime for testing.

For more controlled deployments and to get rid of "works on my computer" -syndrome, we always
make sure our software works under docker.

It's also a quick way to get started with a standard development environment.

SSH agent forwarding
^^^^^^^^^^^^^^^^^^^^

We need buildkit_::

    export DOCKER_BUILDKIT=1

.. _buildkit: https://docs.docker.com/develop/develop-images/build_enhancements/

And also the exact way for forwarding agent to running instance is different on OSX::

    export DOCKER_SSHAGENT="-v /run/host-services/ssh-auth.sock:/run/host-services/ssh-auth.sock -e SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock"

and Linux::

    export DOCKER_SSHAGENT="-v $SSH_AUTH_SOCK:$SSH_AUTH_SOCK -e SSH_AUTH_SOCK"

Creating a development container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build image, create container and start it::

    docker build --ssh default --target devel_shell -t takrmapi:devel_shell .
    docker create --name takrmapi_devel -v `pwd`":/app" -it `echo $DOCKER_SSHAGENT` takrmapi:devel_shell
    docker start -i takrmapi_devel

pre-commit considerations
^^^^^^^^^^^^^^^^^^^^^^^^^

If working in Docker instead of native env you need to run the pre-commit checks in docker too::

    docker exec -i takrmapi_devel /bin/bash -c "uv run prek install --install-hooks"
    docker exec -i takrmapi_devel /bin/bash -c "uv run prek run --all-files"

You need to have the container running, see above. Or alternatively use the docker run syntax but using
the running container is faster::

    docker run --rm -it -v `pwd`":/app" takrmapi:devel_shell -c "uv run prek run --all-files"

Test suite
^^^^^^^^^^

You can use the devel shell to run py.test when doing development, for CI use
the "tox" target in the Dockerfile::

    docker build --ssh default --target tox -t takrmapi:tox .
    docker run --rm -it -v `pwd`":/app" `echo $DOCKER_SSHAGENT` takrmapi:tox

Production docker
^^^^^^^^^^^^^^^^^

There's a "production" target as well for running the application, remember to change that
architecture tag to arm64 if building on ARM::

    docker build --ssh default --target production -t takrmapi:amd64-latest .
    docker run -it --name takrmapi takrmapi:amd64-latest

Development
-----------

TLDR:

- Create and activate a Python 3.11 virtualenv (assuming virtualenvwrapper)::

    mkvirtualenv -p `which python3.11` my_virtualenv

- change to a branch::

    git checkout -b my_branch

- install uv: https://docs.astral.sh/uv/getting-started/installation/
- Install project deps and pre-commit hooks::

    uv sync
    uv run prek install
    uv run prek run --all-files

- Ready to go.

Remember to activate your virtualenv whenever working on the repo, this is needed
because pylint and mypy pre-commit hooks use the "system" python for now (because reasons).

Product credentials
-------------------

The TAK initializer provisions the product certificate through RMAPI and CFSSL.
Mount its credentials volume at ``/data/persistent`` in this container too.
``container-init.sh`` checks for ``public/mtlsclient.pem`` and
``private/mtlsclient.key`` before starting; it does not consume the manifest's
single-use CSR token. Start ``takinit`` before the TAK services and this bridge.

Versioning
----------

Versioning is handled with bump-my-version_. To increment, use ``bump-my-version bump <patch/minor/major>``.

You can use ``bump-my-version show-bump`` to see how each option would affect the version.

.. _bump-my-version: https://github.com/callowayproject/bump-my-version
