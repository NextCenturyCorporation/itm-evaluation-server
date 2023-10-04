import connexion
from ..itm import ITMFileService

def get_ui_file_asset(file_name: str):  # noqa: E501
    """Gets a file from S3.

    Gets a file from S3 bucket for itm-evaluation-dashboard use. # noqa: E501

    :param file_name: Name for file to be retrieved.
    :type file_name: str

    :rtype: str
    """
    return ITMFileService().retrieve_file(file_name)
