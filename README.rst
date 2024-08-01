miniwdl-grid
=============
Extends miniwdl to run workflows on GRID clusters in singularity containers.

This `GRID backend
<https://miniwdl.readthedocs.io/en/latest/runner_backends.html>`_ plugin for
`miniwdl <https://github.com/chanzuckerberg/miniwdl>`_ runs WDL task containers
by creating a job script that is submitted to a GRID cluster. In case the job
description has a container, singularity will be used as container runtime.

Installation
------------

For the development version::

    git clone https://github.com/williamrowell/miniwdl-grid.git

    cd miniwdl-grid

    pip install .

Configuration
--------------
The following `miniwdl configuration
<https://miniwdl.readthedocs.io/en/latest/runner_reference.html#configuration>`_
example can be used to use miniwdl on a GRID cluster:

.. code-block:: ini

    [scheduler]
    container_backend=grid_singularity
    # task_concurrency defaults to the number of processors on the system.
    # since we submit the jobs to SGE this is not necessary.
    # higher numbers means miniwdl has to monitor more processes simultaneously
    # which might impact performance.
    task_concurrency=200

    # This setting allows running tasks to continue, even if one other tasks fails.
    # Useful in combination with call caching. Prevents wasting resources by
    # cancelling jobs half-way that would probably succeed.
    fail_fast = false

    [call_cache]
    # The following settings create a call cache under the current directory.
    # This prevents wasting unnecessary resources on the cluster by rerunning
    # jobs that have already succeeded.
    put = true
    get = true
    dir = "$PWD/miniwdl_call_cache"

    [task_runtime]
    # Setting a 'maxRetries' default allows jobs that fail due to intermittent
    # errors on the cluster to be retried.
    # default queue will be used for all tasks
    # default memory is set to 8GB, all of our tasks will override this
    # default docker will always be overridden by our tasks
    defaults = {
            "maxRetries": 2,
            "docker": "ubuntu:20.04",
            "memory": 8000000000,
            "grid_queue": "default"
        }

    [singularity]
    # This plugin wraps the singularity backend. Make sure the settings are
    # appropriate for your cluster.
    exe = ["singularity"]

    # the miniwdl default options contain options to run as a fake root, which
    # is not available on most clusters.
    run_options = ["--containall"]

    # Location of the singularity images (optional). The miniwdl-grid plugin
    # will set it to a directory inside $PWD. This location must be reachable
    # for the submit nodes.
    image_cache = "$PWD/miniwdl_singularity_cache"

    [grid]
    # extra arguments passed to every qsub command (optional).
    extra_args=""
