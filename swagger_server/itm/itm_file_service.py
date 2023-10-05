import boto3
import filecmp

class ITMFileService:
    """
    Class used to be a proxy for AWS s3 buckets
    """
    def __init__(self):
        # bucket for ui assets
        self.ui_asset_bucket = ""

    def list_files():
        """
        returns list of file names stored in s3 bucket
        """
        fileList = []
        session = boto3.Session()
        s3 = session.resource('s3')
        bucket = s3.Bucket('itm-safe')
        for obj in bucket.objects.all():
            fileList.append(obj.key)
            print(obj.key)
        return fileList

    def retrieve_file(file_name: str) -> any:
        """
       returns file

        Args:
            file_name: name of file to retrieve
        """
        print("inside service proper")
        session = boto3.Session()
        s3 = session.resource('s3')
        bucket = s3.Bucket('itm-safe')
        for obj in bucket.objects.all():
            print(obj.key)
        return None