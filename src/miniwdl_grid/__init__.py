# Copyright (c) 2022 Leiden University Medical Center
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import os
import shlex
import sys
from contextlib import ExitStack
from typing import Dict, List

from WDL import Type, Value
from WDL.runtime import config
from WDL.runtime.backend.cli_subprocess import _SubprocessScheduler
from WDL.runtime.backend.singularity import SingularityContainer


class GridSingularity(SingularityContainer):
    @classmethod
    def global_init(cls, cfg: config.Loader, logger: logging.Logger) -> None:
        # Set resources to maxsize. The base class (_SubProcessScheduler)
        # looks at the resources of the current host, but since we are
        # dealing with a cluster these limits do not apply.
        cls._resource_limits = {
            "cpu": sys.maxsize,
            "mem_bytes": sys.maxsize
        }
        _SubprocessScheduler.global_init(cls._resource_limits)
        # Since we run on the cluster, the images need to be placed in a
        # shared directory. The singularity cache itself cannot be shared
        # across nodes, as it can become corrupted when nodes pull the same
        # image. The solution is to pull image to a shared directory on the
        # submit node. If no image_cache is given, simply place a folder in
        # the current working directory.
        if cfg.get("singularity", "image_cache") == "":
            cfg.override(
                {"singularity": {
                    "image_cache": os.path.join(os.getcwd(),
                                                "miniwdl_singularity_cache")
                }}
            )
        SingularityContainer.global_init(cfg, logger)

    @classmethod
    def detect_resource_limits(cls, cfg: config.Loader,
                               logger: logging.Logger) -> Dict[str, int]:
        return cls._resource_limits  # type: ignore

    @property
    def cli_name(self) -> str:
        return "grid_singularity"

    def process_runtime(self,
                        logger: logging.Logger,
                        runtime_eval: Dict[str, Value.Base]) -> None:
        """Any non-default runtime variables can be parsed here"""
        super().process_runtime(logger, runtime_eval)

        if "grid_queue" in runtime_eval:
            grid_queue = runtime_eval["grid_queue"].coerce(
                Type.String()).value
            self.runtime_values["grid_queue"] = grid_queue

    def _grid_invocation(self): 
        grid_args = [
            "qsub",
            "-b", "yes",        # binary ccommand
            "-now", "no",       # add the job to the pending queue
            "-sync", "yes",     # wait for the job to complete
            "-S", "/bin/bash",  # job shell
            "-V",               # export all environment variables
            "-R", "yes",        # create a reservation
            "-N", self.run_id,  # job name
        ]

        queue = self.runtime_values.get("grid_queue", None)
        if queue is not None:
            grid_args.extend(["-q", queue])

        cpu = self.runtime_values.get("cpu", None)
        if cpu is not None:
            grid_args.extend(["-pe", "smp", str(cpu)])

        memory = self.runtime_values.get("memory_reservation", None)
        if memory is not None:
            # Divide by the number of CPUs to get "memory per slot".
            # Round to the nearest megabyte.
            grid_args.extend(["-l", f"mem_free={round(memory / cpu if cpu else 1 / (1024 ** 2))}M"])

        if self.cfg.has_section("grid"):
            extra_args = self.cfg.get("grid", "extra_args")
            if extra_args is not None:
                grid_args.extend(shlex.split(extra_args))
        print(grid_args)
        return grid_args

    def _run_invocation(self, logger: logging.Logger, cleanup: ExitStack,
                        image: str) -> List[str]:
        singularity_command = super()._run_invocation(logger, cleanup, image)

        grid_invocation = self._grid_invocation()
        grid_invocation.extend(singularity_command)
        logger.info("Grid invocation: " + ' '.join(
            shlex.quote(part) for part in grid_invocation))
        return grid_invocation
