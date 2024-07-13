import platform

ffmpeg_cmdstring = lambda filename, width, height: [
    "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg",
    "-y",  # overwrite the file w/o warning
    "-r",
    "%f" % 60.0,  # frame rate of encoded video
    "-an",  # no audio
    "-analyzeduration",
    "0",  # skip auto codec analysis
    # input params
    "-s",
    f"{width}x{height}",  # Panda's window size
    "-f",
    "rawvideo",  # RamImage buffer is raw buffer
    "-pix_fmt",
    "bgra",  # format of panda texure RamImage buffer
    "-i",
    "-",  # this means a pipe
    "-vf",
    "vflip",  # Since our input is actually flipped upside down, this flag flips it back up.
    # output params
    "-vcodec",
    "libx264",  # Encode into H.264
    # 'mpeg4',
    f"{filename}.mp4",
]
