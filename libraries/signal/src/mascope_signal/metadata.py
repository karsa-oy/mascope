"""Metadata access for H5 and RAW files"""

import mascope_file.name as m_name
from mascope_thermo.thermo import RawFileMetadata


def metadata_factory(base_filename: str, **kwargs):
    """Factory function to create appropriate metadata object based on sample type

    :param base_filename: Sample file name
    :type base_filename: str
    :raises NotImplementedError: If the sample type is unsupported
    :return: Metadata object corresponding to the sample type
    :rtype: RawFileMetadata
    """
    sample_type = m_name.get_sample_file_type(base_filename)
    match sample_type:
        case "orbi_raw":
            datafile_path = m_name.filename_to_datafile_path(base_filename)
            return RawFileMetadata(datafile_path, **kwargs)
        case _:
            raise NotImplementedError(f"Unsupported sample type: {sample_type}")
