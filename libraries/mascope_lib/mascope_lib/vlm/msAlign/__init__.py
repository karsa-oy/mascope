from .ActiveSequence import ActiveSequence
from .Heap import Heap


def remove_overlaps(tentative_alignment_point: str, window_size: float):
    alignment_point = []

    n = len(tentative_alignment_point)

    is_overlapping = [False] * n

    if n == 0:
        return tentative_alignment_point

    for i, mz in enumerate(tentative_alignment_point[:-1]):
        next_mz = tentative_alignment_point[i + 1]
        if (1.0 + window_size) * mz >= (1.0 - window_size) * next_mz:
            is_overlapping[i] = True
            is_overlapping[i + 1] = True

    for i, mz in enumerate(tentative_alignment_point):
        if not is_overlapping[i]:
            alignment_point.append(mz)

    return alignment_point, is_overlapping


def alignment_point_detection(
    peaks: list, window_size: float, for_vlm: bool, ref_spec: int
):
    num_spectra = len(peaks)

    heap = Heap()
    heap.make_heap(peaks)
    active_sequence = ActiveSequence(num_spectra, window_size, for_vlm, ref_spec)

    found = False
    tentative_alignment_point = []
    tentative_vlm_list = []
    while not heap.empty():
        if active_sequence.is_valid(heap):
            found = True

        if not active_sequence.insert(heap, peaks):
            if found:
                tentative_alignment_point.append(active_sequence.mz_avg)
                tentative_vlm_list.append(active_sequence._the_list)
                found = False
            active_sequence.advance_lower_bound()
        else:
            if heap.empty():
                while not active_sequence.empty():
                    if active_sequence.is_valid(heap):
                        tentative_alignment_point.append(active_sequence.mz_avg)
                        tentative_vlm_list.append(active_sequence._the_list)
                        break
                    active_sequence.advance_lower_bound()

    alignment_points, is_overlapping = remove_overlaps(
        tentative_alignment_point, window_size
    )
    vlm_list = [
        vlm for i, vlm in enumerate(tentative_vlm_list) if not is_overlapping[i]
    ]
    return alignment_points, vlm_list


def find_vlm(peaks: list, window_size: float, ref_spec: int):
    for_vlm = True
    return alignment_point_detection(peaks, window_size, for_vlm, ref_spec)


def find_alpt(peaks: list, window_size: float, ref_spec: int):
    for_vlm = False
    return alignment_point_detection(peaks, window_size, for_vlm, ref_spec)[0]
