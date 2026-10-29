from .__version__ import __version__
import subprocess
import json
import os
from urllib.parse import urlparse
from b_hunters.bhunter import BHunters
from karton.core import Task
import shutil
import re
from bson.objectid import ObjectId

class katanam(BHunters):
    """
    B-Hunters-Katana developed by 0xBormaa
    """

    identity = "B-Hunters-Katana"
    version = __version__
    persistent = True
    filters = [
        {
            "type": "url", "stage": "new"
        },
        {
            "type": "path", "stage": "new"
        }
        ,
        {
            "type": "subdomain", "stage": "new"
        }
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def header_args(self,headers):
        """The arguments that give katana the session headers.

        Katana takes them as ``-H "name: value"`` and sends them with
        every request it makes.
        """
        args=[]
        for name,value in headers.items():
            args += ["-H", f"{name}: {value}"]
        return args

    def paths_payload(self,task,domain,urlstripped,path_list=None):
        """The payload of the paths task this crawler publishes.

        The session of the target travels with the task: the scanners
        that consume it have to send the same headers the crawler did.
        """
        payload = {
            "data": urlstripped,
            "subdomain": domain,
            "source": "katana",
            "auth": self.auth_payload(task),
        }
        if path_list is not None:
            payload["path_list"] = path_list
        return payload

    def scan(self,url,headers):
        result=self.katanacommand(url,headers)

        return result
    def katanacommand(self,url,headers):
        result=[]

        try:
            outputfile=self.generate_random_filename()
            output = subprocess.run(["katana","-jc","-jsl","-hl","-nc","-o",outputfile,"-u", url ]+self.header_args(headers), capture_output=True, text=True, timeout=900)
            data=output.stdout.split("\n")
            try:
                
                # Open the file in read mode
                if os.path.exists(outputfile):
                    with open(outputfile, "r") as file:
                        # Read the contents of the file
                        file_contents = file.read()
                        data=file_contents.split("\n")
                        result=data
                    os.remove(outputfile)
            except Exception as e:
                self.log.error(e)
                                


        except Exception as e:
            print("error ",e)
            # result=[]
        return result
    
    def process(self, task: Task) -> None:
        source=task.payload["source"]
        url = task.payload["data"]
        domain = task.payload["subdomain"]
        db=self.db
        collection = db["domains"]
        report_id=task.payload_persistent["report_id"]
        scan_id=task.payload_persistent["scan_id"]
        try:
                
            self.log.info("Starting processing new url")
            self.log.warning(url)
            domain = re.sub(r'^https?://', '', domain)
            domain = domain.rstrip('/')
            self.update_task_status(domain,"Started")
            headers=self.auth_headers(task)
            result=self.scan(url,headers)
            urlstripped = re.sub(r'^https?://', '', url)
            urlstripped = urlstripped.rstrip('/')
            result = list(set(result))
            self.waitformongo()
            db=self.db
            collection = db["links"]
            existing_document = collection.find_one({"report_id":ObjectId(report_id),"source":self.identity})
            new_links=[]
            existing_links=[]
            if existing_document:
                existing_links = existing_document.get("Links", [])
                new_links = [link for link in result if link not in existing_links]
            else:
                new_links=result

            if new_links !=[] and new_links!=[url]:
                resultdata = "\n".join(map(lambda x: str(x), new_links)).encode()
                self.log.info("Uploading data of "+url)
                senddata=self.backend.upload_object("bhunters","katana_"+scan_id+"_"+self.encode_filename(urlstripped),resultdata)
                
                collection.update_one({"report_id": ObjectId(report_id),"source":self.identity}, {"$push": {f"Links": {"$each": new_links}}}, upsert=True)
                tag_task = Task(
                    {"type": "paths", "stage": "scan"},
                    payload=self.paths_payload(task, domain, urlstripped)
                )
                self.send_task(tag_task)

            jsdata=[]
            for i in result:
                
                if ".js" in i and i !="":
                    
                    try:
                        if self.checkjs(i):

                            collection2 = db["js"]
                            existing_document = collection2.find_one({"report_id":ObjectId(report_id),"url": i})
                            if existing_document is None:
                                jsdata.append(i)
                                tag_task = Task(
                                    {"type": "js", "stage": "new"},
                                    payload={"data": url,
                                    "subdomain":domain,
                                    "file": i,
                                    "module":"katana"
                                    }
                                )
                                self.send_task(tag_task)
                    except Exception as e:
                        raise Exception(e)
    
            self.update_task_status(domain,"Finished")

        except Exception as e:
            self.update_task_status(domain,"Failed")
            raise Exception(e)
