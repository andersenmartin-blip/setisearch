#include <math.h>
#include <stddef.h>
#include <stdint.h>

#include <omp.h>

#ifndef M37_CALIBRATION_SOURCE_SHA256
#error "M37_CALIBRATION_SOURCE_SHA256 must be supplied by the verified builder"
#endif

#ifndef M37_CALIBRATION_ALGORITHM_SHA256
#error "M37_CALIBRATION_ALGORITHM_SHA256 must be supplied by the verified builder"
#endif

/*
 * This ABI is deliberately small.  One OpenMP iteration owns one complete
 * scramble and writes exactly one double, so scheduling and thread count
 * cannot change the reduction order within a result.
 */
#define M37_CALIBRATION_ABI "seti-repeater-m37-null-maxima-abi-v1"

const char *m37_calibration_kernel_abi(void) {
    return M37_CALIBRATION_ABI;
}

const char *m37_calibration_kernel_source_sha256(void) {
    return M37_CALIBRATION_SOURCE_SHA256;
}

const char *m37_calibration_kernel_algorithm_sha256(void) {
    return M37_CALIBRATION_ALGORITHM_SHA256;
}

int m37_calibration_kernel_openmp_version(void) {
    return _OPENMP;
}

int m37_calibration_kernel_max_threads(void) {
    return omp_get_max_threads();
}

static inline size_t rolled_index(
    const size_t output_index,
    const size_t positive_shift,
    const size_t length
) {
    if (output_index >= positive_shift) {
        return output_index - positive_shift;
    }
    return length - (positive_shift - output_index);
}

static inline void retain_finite_score(float *best, const float score) {
    /* NumPy's nan_to_num maps both multiplication overflow and NaN to -inf. */
    if (isfinite(score) && score > *best) {
        *best = score;
    }
}

/*
 * Return codes:
 *   0: success
 *   1: null pointer
 *   2: invalid dimensions/thread count
 *   3: a shift is outside [0, q)
 *
 * Python verifies all inputs before crossing the ABI.  The checks here are a
 * second, inexpensive guard against memory-unsafe calls.
 */
int m37_calibration_null_maxima(
    const float *vectors,
    const uint8_t *mask,
    const int64_t *shifts,
    const size_t q,
    const size_t scramble_count,
    const int thread_count,
    double *output
) {
    if (vectors == NULL || mask == NULL || shifts == NULL || output == NULL) {
        return 1;
    }
    if (q == 0 || scramble_count == 0 || thread_count < 1) {
        return 2;
    }

    for (size_t scramble = 0; scramble < scramble_count; ++scramble) {
        for (size_t epoch = 0; epoch < 3; ++epoch) {
            const int64_t shift = shifts[3 * scramble + epoch];
            if (shift < 0 || (uint64_t)shift >= (uint64_t)q) {
                return 3;
            }
        }
    }

    /* Exact float32 encodings of np.float32(math.sqrt(2/3)). */
    const float sqrt_two = 0x1.6a09e6p+0f;
    const float sqrt_three = 0x1.bb67aep+0f;
    const float floor_snr = 3.0f;

    #pragma omp parallel for schedule(static) num_threads(thread_count)
    for (size_t scramble = 0; scramble < scramble_count; ++scramble) {
        const size_t shift0 = (size_t)shifts[3 * scramble];
        const size_t shift1 = (size_t)shifts[3 * scramble + 1];
        const size_t shift2 = (size_t)shifts[3 * scramble + 2];
        float best = -INFINITY;

        for (size_t j = 0; j < q; ++j) {
            const size_t index0 = rolled_index(j, shift0, q);
            const size_t index1 = rolled_index(j, shift1, q);
            const size_t index2 = rolled_index(j, shift2, q);
            const float value0 = vectors[index0];
            const float value1 = vectors[q + index1];
            const float value2 = vectors[2 * q + index2];
            const int eligible0 = value0 >= floor_snr && mask[index0] == 0;
            const int eligible1 = value1 >= floor_snr && mask[q + index1] == 0;
            const int eligible2 = value2 >= floor_snr && mask[2 * q + index2] == 0;

            if (eligible0 && eligible1) {
                const float minimum = value0 < value1 ? value0 : value1;
                retain_finite_score(&best, minimum * sqrt_two);
            }
            if (eligible0 && eligible2) {
                const float minimum = value0 < value2 ? value0 : value2;
                retain_finite_score(&best, minimum * sqrt_two);
            }
            if (eligible1 && eligible2) {
                const float minimum = value1 < value2 ? value1 : value2;
                retain_finite_score(&best, minimum * sqrt_two);
            }
            if (eligible0 && eligible1 && eligible2) {
                float minimum = value0 < value1 ? value0 : value1;
                minimum = minimum < value2 ? minimum : value2;
                retain_finite_score(&best, minimum * sqrt_three);
            }
        }
        output[scramble] = (double)best;
    }
    return 0;
}
