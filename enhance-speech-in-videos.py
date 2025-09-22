#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["joblib", "ffmpeg-python"]
# ///

# this script enhances speech in video files by reducing noise using a rnn model with ffmpeg.
# processing is parallelized and persisted by joblib (so repeat invocations don't do repeat work)
# todo: accept parameters on command line instead of requiring the script to be edited
# needs a rnnn file to run

# files to process
file_glob_pattern = "./**/*.mp4"
# where to persist info about completed jobs
job_cache_dir = "./job_cache"

# prefix for output file names. relative to pwd
output_fn_prefix = "processed-"
output_audio_sample_rate = 48000

# how much parallelism
n_jobs=4

# name of a model, e.g. from https://github.com/GregorR/rnnoise-models
rnn_file = "bd.rnnn"

# db to boost the audio by
gain=0 # i used 13 before, but adjust depending on the input video

import glob
# used for parallelism & persistence; so we don't re-process the same file
import joblib
# invokes ffmpeg in a way that is less painful
import ffmpeg

from joblib import Memory
mem = Memory(job_cache_dir, verbose=1)

def inputs(justOne: bool):
    files = glob.glob(file_glob_pattern)
    for f in files:
        yield f
        if justOne:
            break # just one

def _process(x, gain, view_graph):
        input = ffmpeg.input(x)
        audio = input.audio
        video = input.video

        # Reduce noise
        audio = audio.filter('arnndn', m='bd.rnnn')
        # Boost audio level
        audio = audio.filter('volume', volume=f"{gain}dB")

        import os.path
        new_name = output_fn_prefix + os.path.basename(x)
        # write output video, copying video stream (we don't need to reencode it)
        out = ffmpeg.output(video, audio, new_name, ar=output_audio_sample_rate, **{'c:v': 'copy'})

        print(out)
        if view_graph:
            ffmpeg.view(out) # show filter graph
        else:
            ffmpeg.run(out)

process = mem.cache(_process)

def main():
    from joblib import Parallel, delayed
    # run in parallel; adjust depending on cpu count
    Parallel(n_jobs=n_jobs)(delayed(process)(x, gain, False) for x in inputs(False))

if __name__ == "__main__":
    main()
