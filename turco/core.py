import os
import json
import glob
import boto3
import jinja2
import datetime
import pandas as pd


class MTurkHelper(object):

    def __init__(self, pay, config_path, secrets_path, template_path, logs_path, xml,
                 control_qualifications_path, qualification_folder_path, src_folder_path, xml_folder_path,
                 out_folder_path, queue_url=None, also_print=True):

        self.pay = pay
        self.config_path = config_path
        self.template_path = template_path
        self.qualification_folder_path = qualification_folder_path
        self.logs_path = logs_path
        self.src_folder_path = src_folder_path
        self.xml = xml
        self.xml_folder_path = xml_folder_path
        self.out_folder_path = out_folder_path
        self.control_qualifications_path = control_qualifications_path
        self.queue_url = queue_url
        self.also_print = also_print
        with open(secrets_path, "r") as f:
            secrets = json.load(f)

        endpoint = "https://mturk-requester.us-east-1.amazonaws.com" if pay else \
                    'https://mturk-requester-sandbox.us-east-1.amazonaws.com'

        self.mturk = boto3.client('mturk',
                                  aws_access_key_id=secrets["access_key"],
                                  aws_secret_access_key=secrets["secret_key"],
                                  region_name='us-east-1',
                                  endpoint_url=endpoint)

        if queue_url is not None:
            self.sqs = boto3.client('sqs',
                                    aws_access_key_id=secrets["access_key"],
                                    aws_secret_access_key=secrets["secret_key"],
                                    region_name='us-east-1')

    """ ==========
    |   Helpers
    =========="""

    def log_append(self, message, also_print=False):
        """ This function logs a message and possibly prints it.

        :param message: String. Message to be logged.
        :param also_print: Boolean. Whether it should be printed or not.
        :return: Nothing.
        """
        with open(self.logs_path, "a+") as f:
            f.write(str(datetime.datetime.now()) + "\n")
            f.write(message + "\n")
            f.write("-" * 25 + "\n")
            if also_print:
                print(message)

    def get_qualification_args(self, qualifications_path):
        """ Utility function which obtains the qualification arguments, which are different depending if we're using
        real money or fake money. Useful both for the bogus qualifications, controlled by control_qualifications.json`,
        and for the questionnaire qualifications, controlled by `*_meta.json` located in qualification_folder_path.

        :param qualifications_path: String. Path to the json qualification folder.
        :return: Appropriate qualification arguments ("RealMoney"|"FakeMoney").
        """

        with open(qualifications_path, "r") as f:
            qualification_arguments = json.load(f)

        if self.pay:
            qualification_arguments_tmp = qualification_arguments["RealMoney"]
        else:
            qualification_arguments_tmp = qualification_arguments["FakeMoney"]

        return qualification_arguments_tmp

    def set_qualification_args(self, qualifications_path, qualification_arguments_tmp):
        """ Utility function which sets the qualification arguments, which are different depending if we're using
        real money or fake money. Usually you obtain them with `get_qualification_args`, modify them, and use this
        to save it back again.

        :param qualifications_path: String. Path to the json qualification folder.
        :param qualification_arguments_tmp: Dictionary. Appropriate qualification arguments ("RealMoney"|"FakeMoney").
        :return: Nothing.
        """

        with open(qualifications_path, "r") as f:
            qualification_arguments = json.load(f)

        if self.pay:
            qualification_arguments["RealMoney"] = qualification_arguments_tmp
        else:
            qualification_arguments["FakeMoney"] = qualification_arguments_tmp

        with open(qualifications_path, "w") as f:
            json.dump(qualification_arguments, f)

    """ =======================
    |   Bogus Qualifications
    ======================= """

    def create_bogus_qualifications(self, name):
        """ This function creates a bogus qualification. It first checks if it already exists, as every qualification is
        assigned to a name in the json file located in ```. If not, it creates it

        :param name: String. Name of the qualification to be created.
        :return: Nothing.
        """

        qualification_arguments_tmp = self.get_qualification_args(self.control_qualifications_path)

        if name in qualification_arguments_tmp:
            self.log_append(
                "QualificationID already exists! ({0})".format(qualification_arguments_tmp[name]),
                also_print=True)
            return

        response = self.mturk.create_qualification_type(Name=name, Keywords="None", Description="None",
                                                        QualificationTypeStatus="Active", AutoGranted=False)

        qualification_arguments_tmp[name] = response["QualificationType"]["QualificationTypeId"]

        self.set_qualification_args(self.control_qualifications_path, qualification_arguments_tmp)

        self.log_append("{0} (Bogus) Qualification {1} was created".format(name, qualification_arguments_tmp[name]),
                        also_print=self.also_print)

    def delete_bogus_qualification(self, name):
        """ This function deletes a bogus qualification. It first checks if it doesn't exist in the first place.

        :param name: String. Name of the qualification to be deleted.
        :return: Nothing.
        """

        qualification_arguments_tmp = self.get_qualification_args(self.control_qualifications_path)

        if name not in qualification_arguments_tmp:
            self.log_append("QualificationID doesn't exist already!", also_print=self.also_print)
            return

        tmp = qualification_arguments_tmp[name]

        qualification_arguments_tmp.pop(name)

        self.mturk.delete_qualification_type(QualificationTypeId=tmp)

        self.set_qualification_args(self.control_qualifications_path, qualification_arguments_tmp)

        self.log_append("{0} (Bogus) Qualification {1} was deleted".format(name, tmp), also_print=self.also_print)

    def assign_bogus_qualification(self, worker_id, qualification_id=None, qualification_name=None):
        """ This function assigns a bogus qualification (given its id or its name) to a worker, given its id.

        :param worker_id: String. Id of the worker that will be assigned with the qualification.
        :param qualification_id: String. Qualification ID as determined by mturk.
        :param qualification_name: String. Qualification name as determined by `self.control_qualifications_path`
        :return: Nothing.
        """

        if qualification_id is None:
            qualification_arguments_tmp = self.get_qualification_args(self.control_qualifications_path)
            qualification_id = qualification_arguments_tmp[qualification_name]

        self.mturk.associate_qualification_with_worker(QualificationTypeId=qualification_id, WorkerId=worker_id,
                                                       IntegerValue=1, SendNotification=False)

        self.log_append("{0} Qualification was assigned to {1}".format(qualification_id, worker_id),
                        also_print=self.also_print)

    def listener_bogus_qualification(self, handle_qualification, sleep_normal=2, sleep_longer=3):
        """ This function should run separately to ensure qualifications are being assigned.

        :param handle_qualification: function to handle the response of a given worker to an assignment, extracting the
        worker id and the qualification name. This qualification will then be assigned to the worker.
        :param sleep_normal: How much time until next request to Amazon SQS in case there is a new assignment.
        :param sleep_longer: How much time until next request to Amazon SQS in case there is no new assignment.
        :return: Nothing.
        """

        while True:

            response = self.sqs.receive_message(QueueUrl=self.queue_url,
                                                AttributeNames=['All'],
                                                MaxNumberOfMessages=10,
                                                WaitTimeSeconds=0
                                                )

            if "Messages" not in response:
                continue

            print(response)

            messages = response["Messages"]

            for message in messages:
                receipt = message["ReceiptHandle"]

                body = json.loads(message["Body"])

                # Case 1
                if "Events" not in body:
                    print("case1")
                    worker_id, qualification_name = handle_qualification(body)
                    print(worker_id, qualification_name)

                    if worker_id is not None and qualification_name is not None:

                        self.assign_bogus_qualification(worker_id=worker_id, qualification_name=qualification_name)

                # Case 2
                else:
                    for answer in body["Events"]:
                        worker_id, qualification_name = handle_qualification(answer)

                        if worker_id is None or qualification_name is None:
                            continue

                        self.assign_bogus_qualification(worker_id=worker_id,
                                                        qualification_name=qualification_name)

                self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt)

    """ ========================
    |   Actual Qualifications
    ======================== """

    def create_qualifications(self):
        """ This function creates all qualifications "bla" given three files located in `self.qualification_folder_path`
            - bla_answers.xml: which contains the answers as specified by amazon mturk.
            - bla_question.xml: which contains the questions as specified by amazon mturk.
            - bla_meta.json: which contains the configuration of the qualification, and the code to retrieve answers.

        :return: Nothing
        """
        for text in glob.glob(os.path.join(self.qualification_folder_path, "*_meta.json")):

            qualification_arguments_tmp = self.get_qualification_args(text)

            if "QualificationID" in qualification_arguments_tmp:
                self.log_append(
                    "QualificationID already exists! ({0})".format(qualification_arguments_tmp["QualificationID"]),
                    also_print=True)
                continue

            prefix = os.path.basename(text)[:-5].split("_")[0]
            directory = os.path.dirname(text)

            questions_key = os.path.join(directory, "{0}_question.xml".format(prefix))
            answer_key = os.path.join(directory, "{0}_answers.xml".format(prefix))

            with open(answer_key, "r") as f:
                answer_key_text = f.read()

            with open(questions_key, "r") as f:
                questions_key_text = f.read()

            qualification_arguments_tmp["Test"] = questions_key_text
            qualification_arguments_tmp["AnswerKey"] = answer_key_text

            response = self.mturk.create_qualification_type(**qualification_arguments_tmp)

            qualification_arguments_tmp.pop("Test")
            qualification_arguments_tmp.pop("AnswerKey")

            qualification_arguments_tmp["QualificationID"] = response["QualificationType"]["QualificationTypeId"]

            self.set_qualification_args(text, qualification_arguments_tmp)

            self.log_append("{0} Qualification {1} was created".format(
                qualification_arguments_tmp["Name"], response["QualificationType"]["QualificationTypeId"]),
                also_print=self.also_print)

    def delete_qualifications(self, names=None):
        """ Given a list of names, this function deletes the corresponding qualifications. If no names are given,
        deletes all existing qualifications.

        :param names: List. List of names to delete.
        :return: Nothing.
        """

        for text in glob.glob(os.path.join(self.qualification_folder_path, "*_meta.json")):

            prefix = os.path.basename(text)[:-5].split("_")[0]

            if names is not None and prefix not in names:
                continue

            qualification_arguments_tmp = self.get_qualification_args(text)

            if "QualificationID" not in qualification_arguments_tmp:
                self.log_append("QualificationID doesn't exist already!", also_print=True)
                continue

            self.mturk.delete_qualification_type(QualificationTypeId=qualification_arguments_tmp["QualificationID"])

            qual_id_old = qualification_arguments_tmp.pop("QualificationID")

            self.set_qualification_args(text, qualification_arguments_tmp)

            self.log_append("{0} Qualification {1} was deleted".format(
                qualification_arguments_tmp["Name"], qual_id_old), also_print=self.also_print)

    def get_qualification_json(self, qual_name, integer):
        """ For a given qualification `bla`, given the score obtained in the qualification & the code in `bla_meta.json`
        retrieves the answers.

        :param qual_name: String. Name of the qualification.
        :param integer: Integer. Score obtained.
        :return: Dictionary. Answers to the qualification.
        """

        text = os.path.join(self.qualification_folder_path, "{0}_meta.json".format(qual_name))

        with open(text, "r") as f:
            qualification_scoring = json.load(f)["Scoring"]

        integer_str = str(integer).zfill(len(qualification_scoring.keys()))

        qualification_json = dict()

        for key in qualification_scoring.keys():
            tmp = str(integer_str[int(key)])
            tmp_json = qualification_scoring[key][tmp]
            qualification_json.update(tmp_json)

        return qualification_json

    """ ============
    |   Questions   
    ============ """

    def create_questions(self, treat_question=lambda x: x):
        """ This function creates a question using a question template, located in `self.template_path` and a series of
        source jsons, located in `self.src_folder_path` notice that they should match, as the template is a jinja2 file
        and the json is fed directly into it. This then creates a XML file as specified in `self.config_path`.

        :param treat_question: Function. This is a optional function that treats the json.
        :return: Nothing.
        """

        with open(self.template_path, "r") as f:
            template_question = jinja2.Template(f.read())

        with open(self.config_path) as f:
            config = json.load(f)

        for text in glob.glob(os.path.join(self.src_folder_path, "*.json")):

            prefix = os.path.basename(text)[:-5]

            with open(text) as f:
                question = json.load(f)

            for k, v in config["commons"].items():
                question[k] = v

            treated_question = treat_question(question)

            rendered = template_question.render(**treated_question)

            dst_path = os.path.join(self.xml_folder_path, "{0}.xml".format(prefix))

            with open(dst_path, "w") as dst:
                dst.write(self.xml.format(rendered))

            self.log_append("Created question {0} from {1}".format(dst_path, text), also_print=self.also_print)

    def publish_questions(self, question_based_blocking_id=False, alter_names=True, precise=None):
        """ This function looks into the xmls in `self.xml_folder_path` and publishes it according to the configs in
        ``self.config_file`. Also


        - It adds custom qualifications so, if you have, in the config file a qualification with "Placeholder": true, it
        will look for its ID in `self.qualification_folder_path` and replace it for the actual qualification.

        - If the flag question_based_blocking_id=True, it will add a constraint requiring that the user doesn't have the
        qualification with the same name as the question name. Notice that this requires that you have created a bogus
        qualification with this name before hand.

        - If you specify a SQS queue (self.queue_url), this function sets the hit to notify it.


        :param question_based_blocking_id: Boolean. Adds constraint based on question name.
        :param alter_names: Boolean. If this is true, adds a different number to each one of the questions.
        :return: Nothing.
        """

        question_map = dict()
        qualification_map = dict()
        idx_title = 0

        with open(self.config_path, "r") as f:
            question_configs = json.load(f)["arguments"]
            original_title = question_configs["Title"]

        if precise is None:
            questions = glob.glob(os.path.join(self.xml_folder_path, "*.xml"))
        else:
            questions = [os.path.join(self.xml_folder_path, "{0}.xml".format(k)) for k in  precise.keys()]

        for question_name in questions:
            with open(question_name, "r") as f:
                question = f.read()

            question_configs["Question"] = question

            # Treats qualifications

            for idx in range(len(question_configs["QualificationRequirements"])):
                if "Placeholder" in question_configs["QualificationRequirements"][idx]:
                    qual_name = question_configs["QualificationRequirements"][idx]["QualificationTypeId"]
                    qualifications_path = os.path.join(self.qualification_folder_path,
                                                       "{0}_meta.json".format(qual_name))

                    qual_id = self.get_qualification_args(qualifications_path)["QualificationID"]

                    question_configs["QualificationRequirements"][idx]["QualificationTypeId"] = qual_id

                    question_configs["QualificationRequirements"][idx].pop("Placeholder")

                    qualification_map[qual_name] = qual_id

            # Adds blocking qualification

            if question_based_blocking_id:
                prefix_original = os.path.basename(question_name)[:-4].split("_")[0]

                qual_id = self.get_qualification_args(self.control_qualifications_path)[prefix_original]

                control_qual_dict = {"QualificationTypeId": qual_id, "Comparator": "DoesNotExist"}

                question_configs["QualificationRequirements"].append(control_qual_dict)

            # Change names
            if alter_names:
                question_configs["Title"] = original_title + " " + str(idx_title)
                idx_title += 1

            # Change max_Assignments:
            if precise is not None:
                question_configs["MaxAssignments"] = precise[os.path.basename(question_name)[:-4]]

            # Creates hit

            new_hit = self.mturk.create_hit(**question_configs)

            # Removes qualification
            if question_based_blocking_id:
                question_configs["QualificationRequirements"].pop(-1)

            if self.pay:
                self.log_append("{0} Hit was created\nhttps://worker.mturk.com/mturk/preview?groupId={1}"
                                .format(new_hit['HIT']['HITId'], new_hit['HIT']['HITGroupId']), also_print=True)
            else:
                self.log_append("{0} Hit was created\nhttps://workersandbox.mturk.com/mturk/preview?groupId={1}"
                                .format(new_hit['HIT']['HITId'], new_hit['HIT']['HITGroupId']), also_print=True)

            question_map[os.path.basename(question_name[:-4])] = new_hit['HIT']['HITId']

            # Creates notifications

            if self.queue_url is not None:
                notification = {'Destination': self.queue_url, 'Transport': 'SQS',
                                'Version': '2014-08-15', 'EventTypes': ['AssignmentSubmitted']}

                self.mturk.update_notification_settings(HITTypeId=new_hit['HIT']['HITTypeId'],
                                                        Notification=notification, Active=True)

        out = {"question_map": question_map, "qualification_map": qualification_map}

        with open(os.path.join(self.out_folder_path, "out_{0}.json").format(datetime.datetime.now()), "w") as f:
            json.dump(out, f)

    def get_replies(self):

        question_map = dict()
        qualification_map = dict()

        for out_name in glob.glob(os.path.join(self.out_folder_path, "out_*.json")):

            with open(out_name, "r") as f:
                tmp = json.load(f)
                question_map.update(tmp["question_map"])
                qualification_map.update(tmp["qualification_map"])

        df_list = []

        for q_id, value in question_map.items():
            worker_results = self.mturk.list_assignments_for_hit(HITId=value)

            for ass in worker_results["Assignments"]:
                ass["TimeSpent"] = ass["SubmitTime"] - ass["AcceptTime"]
                ass["Question"] = q_id

                for qual_name, qual_id in qualification_map.items():
                    response = self.mturk.get_qualification_score(WorkerId=ass["WorkerId"],
                                                                  QualificationTypeId=qual_id)

                    qualification_json = self.get_qualification_json(qual_name,
                                                                     response["Qualification"]["IntegerValue"])

                    ass["{0}:{1}".format(qual_name, qual_id)] = json.dumps(qualification_json)

                df_list.append(ass)

        df = pd.DataFrame(df_list)

        df.to_csv(os.path.join(self.out_folder_path, "results_{0}.csv").format(datetime.datetime.now()), index=False)
