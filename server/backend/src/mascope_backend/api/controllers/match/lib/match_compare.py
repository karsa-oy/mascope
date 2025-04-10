from mascope_backend.runtime import runtime

logger = runtime.logger


def compare_match_samples(samples_data: list, match_samples: list) -> list:
    """
    Compare match-related fields between the samples data (db stored) and aggregated match_samples data,
    log a warning if any mismatch is found, and return mismatched samples.

    :param samples_data: List of samples with match data from get_samples (db stored).
    :param match_samples: List of match samples from the aggregated data (aggregated from match_isotope level).
    :return: A list of mismatches containing information about samples with mismatches.
    """
    mismatches_info = []

    for sample in samples_data:
        for match_sample in match_samples:
            if sample["sample_item_id"] == match_sample["sample_item_id"]:
                # Compare the fields
                mismatches = []
                if sample.get("match_score") != match_sample.get("match_score"):
                    mismatches.append(
                        f"match_score: {sample.get('match_score')} != {match_sample.get('match_score')}"
                    )
                if sample.get("match_category") != match_sample.get("match_category"):
                    mismatches.append(
                        f"match_category: {sample.get('match_category')} != {match_sample.get('match_category')}"
                    )
                if sample.get("sample_peak_intensity_mean") != match_sample.get(
                    "sample_peak_intensity_mean"
                ):
                    mismatches.append(
                        f"sample_peak_intensity_mean: {sample.get('sample_peak_intensity_mean')} != {match_sample.get('sample_peak_intensity_mean')}"
                    )
                if sample.get("sample_peak_interference_sum") != match_sample.get(
                    "sample_peak_interference_sum"
                ):
                    mismatches.append(
                        f"sample_peak_interference_sum: {sample.get('sample_peak_interference_sum')} != {match_sample.get('sample_peak_interference_sum')}"
                    )

                # Log warnings if mismatches are found
                if mismatches:
                    logger.warning(
                        f"Mismatch in sample {sample['sample_item_name']} (ID {sample['sample_item_id']}): {', '.join(mismatches)}"
                    )
                    mismatches_info.append(
                        {
                            "sample_item_id": sample["sample_item_id"],
                            "sample_item_name": sample["sample_item_name"],
                            "mismatches": mismatches,
                        }
                    )

    return mismatches_info
