# turco

*turco* is a easy to use library that automates a bunch of stuff in Amazon mechanical turk! It is also coupled with a "best practices" guide for mturk, which can be found [here](). *turco* enables its users to follow a simple (but elegant) pipeline:


## Quickstart

To get started with *turco*, you simply have to run:

    turco-init -p my-hit 
    
This will create the following file structure:

    my-hit/
        out/
            hit_example.json
        src/
        xml/
        config.json
        default_args.json
        secrets.json
        secrets_with_money.json
        template.html

This may sounds daunting at first, but lets break down what to do with all these config files at the pipeline level.

### Create Questions

In order to create questions, we need two things: A template and data. 
We use the jinja2 templating library, as portrayed by:

    my-hit/
        ...
        template.html

This is nothing more than a Jinja2 html template that will be rendered inside a [HTMLQuestion][1] (a data structure provided by amazon). What goes "inside" the template changes for each different hit (duh). For each HIT we want to create, we simply have to create a corresponding `.json` file in the `my-hit/out/` folder!

So for example, in the stub we create, we have the following template:


    ...
    <div class="panel-body">
        <p>You will be given {{num_tweets}} tweets (up to {{number_characters}} chars). </p>
        <p>Your task is to: </p>
    ...

    {% for tweet_id, tweet_text in tweets %}
    ...
        <div>{{tweet_text}}</div>
    ...
        <label>Is the tweet related to food poisoning?</label>
        <select name="choice_{{tweet_id}}" id="choice_{{tweet_id}}" class="form-control" form="mturk_form">
            <option disabled selected value>-- select an option --</option>
            <option value="Yes">Yes</option>
            <option value="No">No</option>
        </select>
    ...
    {% endfor %}
    ...
    
Notice that the "insertion points" are `num_tweets`, `number_characters` and `tweets`. The latter which is a list containing tuples of `tweet_id, tweet_text`. The jsons in the `src/` folder must simply match the variables referenced in the template. So for example, a possible json would be:

    {
        "num_tweets": 3,
        "number_characters": 280,
        "tweets": [
                ["1","text tweet 1"], 
                ["2","text tweet 2"], 
                ["3","text tweet 3"]]
    }
    
We can then simply run:

    turco-create-questions -p my-hit 

This will create a xml question in the `xml` folder for each json file in `src` folder.

### Manage Configurations

When we initialized the turco project folder with `turco-init` we created 4 config files, which we approach in turk.

- `secrets.json`

Here you should put your AWS Access Keys, which you can get [here](2).

- `default_args.json`

Here you have a bunch of default paths. You should't need to mess with these, unless you want, for example, to change the destination of your source jsons, or the destination of your xml questions.

- `config.json`

This is "the real deal", it contain two main arguments `commons` and `arguments`. The `commons` argument basically are things that will be inserted in all the `.src` files. So for example, if you could simple put:

    {
        "commons": { "number_characters": 280 }
    }
    
And then any `{{number_characters}}` in the template would be replaced by 280. Mostly, this allows to leave your template clean and generic!

The `arguments` argument (duh), contains the arguments which will be passed when creating the HIT on AMT. It allows you to specify any argument in [here](3). Bellow we have an example:

    "Title": "Classify Tweets (Food poisoning)",
    "Description": "Decide whether the tweet is related to food poisoning",
    "Keywords": "summarization, writing, research",
    "Reward": "0.10",
    "MaxAssignments": 3,
    "LifetimeInSeconds": 500000,
    "AssignmentDurationInSeconds": 3600,
    "AutoApprovalDelayInSeconds": 28800,
    "Question": false,
    "QualificationRequirements": [
      {
        "QualificationTypeId": "000000000000000000L0",
        "Comparator": "GreaterThan",
        "IntegerValues": [
          98
        ]
        ...
      }
    ]

Notice that the qualifications that we put here are only standard qualifications. More on creating custom qualifications can be found in a specific guide.

### Publish Questions

Publishing questions is as simple as:

    turco-publish-questions -p my-hit 

Notice that by default we create the questions on MTurk sandbox. However, if you want to create actual questions, simply do:

    turco-publish-questions -p my-hit -pay

### Retrieve Questions


To retrieve questions, simply run:

    turco-create-questions -p my-hit 

Notice that if you created payed questions you must include the `-pay` flag.

    turco-create-questions -p my-hit -pay



[1]: https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_HTMLQuestionArticle.html
[2]:https://console.aws.amazon.com/iam/home?#/security_credential
[3]:https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_CreateHITOperation.html