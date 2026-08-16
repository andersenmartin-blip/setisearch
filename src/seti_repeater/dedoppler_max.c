#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/*
 * For every safe starting-frequency bin, retain the strongest straight-line
 * drift path. Input rows must already be flattened and robustly normalized.
 */
int dedoppler_max(
    const float *data,
    int ntime,
    int nfreq,
    int max_shift,
    float *best_snr,
    int32_t *best_shift
) {
    if (!data || !best_snr || !best_shift || ntime < 2 || nfreq <= 2 * max_shift) {
        return 1;
    }
    const int nvalid = nfreq - 2 * max_shift;
    const int nthreads = omp_get_max_threads();
    float *thread_best = (float *)malloc((size_t)nthreads * nvalid * sizeof(float));
    int32_t *thread_shift = (int32_t *)malloc((size_t)nthreads * nvalid * sizeof(int32_t));
    if (!thread_best || !thread_shift) {
        free(thread_best);
        free(thread_shift);
        return 2;
    }

    #pragma omp parallel
    {
        const int tid = omp_get_thread_num();
        float *local_best = thread_best + (size_t)tid * nvalid;
        int32_t *local_shift = thread_shift + (size_t)tid * nvalid;
        float *sums = (float *)malloc((size_t)nvalid * sizeof(float));
        for (int j = 0; j < nvalid; ++j) {
            local_best[j] = -1.0e30f;
            local_shift[j] = 0;
        }

        #pragma omp for schedule(static)
        for (int displacement = -max_shift; displacement <= max_shift; ++displacement) {
            memset(sums, 0, (size_t)nvalid * sizeof(float));
            for (int t = 0; t < ntime; ++t) {
                const int shift = (int)lround((double)displacement * t / (ntime - 1));
                const float *row = data + (size_t)t * nfreq + max_shift + shift;
                #pragma omp simd
                for (int j = 0; j < nvalid; ++j) {
                    sums[j] += row[j];
                }
            }
            const float scale = 1.0f / sqrtf((float)ntime);
            #pragma omp simd
            for (int j = 0; j < nvalid; ++j) {
                const float snr = sums[j] * scale;
                if (snr > local_best[j]) {
                    local_best[j] = snr;
                    local_shift[j] = displacement;
                }
            }
        }
        free(sums);
    }

    for (int j = 0; j < nvalid; ++j) {
        float value = -1.0e30f;
        int32_t displacement = 0;
        for (int tid = 0; tid < nthreads; ++tid) {
            const float candidate = thread_best[(size_t)tid * nvalid + j];
            if (candidate > value) {
                value = candidate;
                displacement = thread_shift[(size_t)tid * nvalid + j];
            }
        }
        best_snr[max_shift + j] = value;
        best_shift[max_shift + j] = displacement;
    }

    free(thread_best);
    free(thread_shift);
    return 0;
}

