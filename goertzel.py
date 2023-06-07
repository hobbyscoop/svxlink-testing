from datetime import datetime
import logging
import math
import numpy as np
import socket
import struct
from time import sleep

logging.basicConfig(filename="/log", level=logging.DEBUG)


def convert_interleaved_to_windowed(raw_bytes, window_size):
    """
    converts the 16 bit, 2 channel interleaved data from svxlink to a single windowed value array
    :param raw_bytes: data coming from the socket
    :param window_size: the window size to sample with
    :return:
    """
    # convert the data stream into 2 byte samples
    raw_data = struct.unpack('<%dh' % (len(raw_bytes) / 2), raw_bytes)

    # Reshape the interleaved samples into two separate channels
    samples = np.array(raw_data).reshape((-1, 2))

    # Extract the desired channel (e.g., left or right) - index 0 for left, 1 for right
    channel = samples[:, 0]  # Modify the index if you want the other channel

    # Apply a windowing function to the channel
    window = np.hamming(len(channel))
    window = np.pad(window, (0, max(0, window_size - len(window))), mode='constant')
    windowed_signal = channel * window[:len(channel)]

    return windowed_signal


def goertzel(samples, sample_rate, *freqs):
    """
    Implementation of the Goertzel algorithm, useful for calculating individual
    terms of a discrete Fourier transform.

    `samples` is a windowed one-dimensional signal originally sampled at `sample_rate`.

    The function returns 2 arrays, one containing the actual frequencies calculated,
    the second the coefficients `(real part, imag part, power)` for each of those frequencies.
    For simple spectral analysis, the power is usually enough.

    Example of usage :
        
        freqs, results = goertzel(some_samples, 44100, (400, 500), (1000, 1100))
    """
    window_size = len(samples)
    f_step = sample_rate / float(window_size)
    f_step_normalized = 1.0 / window_size

    # Calculate all the DFT bins we have to compute to include frequencies in `freqs`.
    bins = set()
    for f_range in freqs:
        f_start, f_end = f_range
        k_start = int(math.floor(f_start / f_step))
        k_end = int(math.ceil(f_end / f_step))

        if k_end > window_size - 1: raise ValueError('frequency out of range %s' % k_end)
        bins = bins.union(range(k_start, k_end))

    # For all the bins, calculate the DFT term
    n_range = range(0, window_size)
    result = {}
    for k in bins:

        # Bin frequency and coefficients for the computation
        f = k * f_step_normalized
        w_real = 2.0 * math.cos(2.0 * math.pi * f)

        # Doing the calculation on the whole sample
        d1, d2 = 0.0, 0.0
        for n in n_range:
            y = samples[n] + w_real * d1 - d2
            d2, d1 = d1, y

        # calculate the power for this bin
        result[f * sample_rate] = d2 ** 2 + d1 ** 2 - w_real * d1 * d2

    # return the frequency for the bucket with the highest power
    return max(result, key=lambda x: result[x])


def find_closest_number(target, numbers):
    closest_number = min(numbers, key=lambda x: abs(x - target))
    return closest_number


if __name__ == '__main__':
    SAMPLE_RATE = 16000
    WINDOW_SIZE = 1024

    logging.info("starting loop")
    while True:
        try:
            # start over every loop, so we don't queue up data
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", 10000))

            # fetch 2 ch, 2 byte samples
            data, _ = sock.recvfrom(SAMPLE_RATE * 2 * 2 * WINDOW_SIZE)
            logging.debug("got {} bytes".format(len(data)))
            samples = convert_interleaved_to_windowed(data, WINDOW_SIZE)

            result = goertzel(samples, SAMPLE_RATE, (200, 400), (500, 700))
            freq = find_closest_number(result, [300, 600])
            logging.debug("writing to file: {}".format(freq))
            with open("/audio", "a") as output:
                # output.write("{} {}\n".format(datetime.now().timestamp(), freq))
                output.write(str(freq)+"\n")
            # print(freq)
            sock.close()

            # rate limit
            logging.info("sleeping")
            sleep(0.1)
        except Exception as e:
            logging.error(e)
