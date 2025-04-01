import json
from thefuzz import process, fuzz
import requests
import urllib.parse

config = None
with open("config.json","r") as f:
    x = f.read()
    config = json.loads(x)

TAG_DETAIL_SEARCH_API_PREFIX = config['TAG_DETAIL_SEARCH_API_PREFIX']
TAG_SEARCH_API = config['TAG_SEARCH_API']
response_tag = requests.get(TAG_SEARCH_API)
response_tag = response_tag.json()['Data']
retrieved_tag_names = [ele['ValuePath'] for ele in response_tag]


HEADERS = {
    "insis_token": config['INSIS_TOKEN'],
    "insis_key": config['INSIS_KEY']
}

def closest_match(text, array, threshold=70, scorerType=0, defaultReturn=0):
        '''
        Fuzzy matching function with different scorer options like:
        0: ratio
        1: partial_ratio
        2: token_sort_ratio
        3: token_set_ratio
        4: partial_token_sort_ratio

        Default return:
        0: text
        1: empty string

        Returns:
        [text,score]
        '''
        closestMatch = None
        score = None

        match scorerType:
            case 0:
                closestMatch, score = process.extractOne(text, array, scorer=fuzz.ratio)
            case 1:
                closestMatch, score = process.extractOne(text, array, scorer=fuzz.partial_ratio)
            case 2:
                closestMatch, score = process.extractOne(text, array, scorer=fuzz.token_sort_ratio)
            case 3:
                closestMatch, score = process.extractOne(text, array, scorer=fuzz.token_set_ratio)
            case 4:
                closestMatch, score = process.extractOne(text, array, scorer=fuzz.partial_token_set_ratio)
            case _:
                closestMatch, score = process.extractOne(text, array, scorer=fuzz.ratio)

        if defaultReturn==0:
            return [closestMatch,score] if score > threshold else [text,0]
        else:
            return [closestMatch,score] if score > threshold else ["",0]

def processRelativeTimeBase(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict = {"Now": "0", "Hour": "10", "Today": "1", "CurrentWeek": "2", "CurrentMonth": "3", "CurrentYear": "4", "Yesterday": "5", "LastWeek": "6", "LastMonth": "7", "LastYear": "8", "Shift": "9", "NextShift": "11"}
    if (('StartRelativeTimeBase' not in response) or response['StartRelativeTimeBase']==None):
        response['StartRelativeTimeBase'] = None
    else:
        value = response['StartRelativeTimeBase']
        response['StartRelativeTimeBase'] = textToValueDict[value] if value else None
    if (('EndRelativeTimeBase' not in response) or response['EndRelativeTimeBase']==None):
        response['EndRelativeTimeBase'] = None
    else:
        value = response['EndRelativeTimeBase']
        response['EndRelativeTimeBase'] = textToValueDict[value] if value else None
   
def processRelativeTimeMultiplier(response):
    '''
    Do not use this function from main.py
    '''
    if('StartRelativeTimeSecondaryOperand' not in response):
        response['StartRelativeTimeMultiplier'] = None
    else:
        response['StartRelativeTimeMultiplier'] = response.pop('StartRelativeTimeSecondaryOperand')
   
    if('EndRelativeTimeSecondaryOperand' not in response):
        response['EndRelativeTimeMultiplier'] = None
    else:
        response['EndRelativeTimeMultiplier'] = response.pop('EndRelativeTimeSecondaryOperand')

def processRelativeTimeIdentifier(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict = {"Minute" : "0", "Hour" : "1", "Day" : "2", "Week" : "3", "Month" : "4", "Quarter" : "5", "Year" : "6"} 
    if('StartRelativeTimeSecondaryOperandUnit' not in response):
        response['StartRelativeTimeIdentifier'] = None
    else:
        value = response.pop('StartRelativeTimeSecondaryOperandUnit')
        response['StartRelativeTimeIdentifier'] = textToValueDict[value] if value else None
    
    if('EndRelativeTimeSecondaryOperandUnit' not in response):
        response['EndRelativeTimeIdentifier'] = None
    else:
        value = response.pop('EndRelativeTimeSecondaryOperandUnit')
        response['EndRelativeTimeIdentifier'] = textToValueDict[value] if value else None

def processOperator(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict = {"-" : "0", "+" : "1"}
    if('StartRelativeTimeOperator' not in response):
         response['StartOperator'] = None
    else:
        value = response.pop('StartRelativeTimeOperator')
        response['StartOperator'] = textToValueDict[value] if value else None
    
    if('EndRelativeTimeOperator' not in response):
         response['EndOperator'] = None
    else:
        value = response.pop('EndRelativeTimeOperator')
        response['EndOperator'] = textToValueDict[value] if value else None

def processIntervalValue(response):
    '''
    Do not use this function from main.py
    '''
    if('TimeIntervalValue' not in response):
        response['IntervalValue'] = None
    else:
        response['IntervalValue'] = response.pop('TimeIntervalValue')

def processIntervalType(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict = {"Minute" : "0", "Hour" : "1", "Day" : "2", "Week" : "3", "Month" : "4", "Quarter" : "5", "Year" : "6", "Second" : "10"} 
    if('TimeIntervalValueUnit' not in response):
        response['IntervalType'] = None
    else:
        value = response.pop('TimeIntervalValueUnit')
        response['IntervalType'] = textToValueDict[value] if value else None

def processIntervalSpread(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict =  {"Before": "0", "After": "1", "Around": "2"}
    if('TimeIntervalSpread' not in response):
        response['IntervalSpread'] = None
    else:
        value = response.pop('TimeIntervalSpread')
        response['IntervalSpread'] = textToValueDict[value] if value else None

def processInfoViewType(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict = {"Grid": "0", "Chart": "1", "Gauge": "2", "Calendar": "3"}
    if('ViewType' not in response):
        response['InfoViewType'] = None
    else:
        value = response.pop('ViewType')
        response['InfoViewType'] = textToValueDict[value] if value else None

def processGaugeType(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict = {"Radial": "0","Linear": "1"}
    if('GaugeType' not in response):
        response['GaugeType'] = None
    else:
        value = response.pop('GaugeType')
        response['GaugeType'] = textToValueDict[value] if value else None

def processGaugeOrientation(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict = {"LinearVertical":"0","LinearHorizontal":"1"}
    if('GaugeOrientation' not in response):
        response['GaugeOrientation'] = None
    else:
        value = response.pop('GaugeOrientation')
        response['GaugeOrientation'] = textToValueDict[value] if value else None

def processInfoViewChartType(response):
    '''
    Do not use this function from main.py
    '''
    textToValueDict = {"Line": "0", "Bar": "1", "Column": "2", "Pie": "3", "Donut": "4", "Funnel": "5", "Bullet": "6", "Scatter": "7", "Bubble": "8", "BoxPlot": "9", "Radar": "11", "Waterfall": "12", "Progress": "13"}
    if('ChartType' not in response):
        response['InfoViewChartType'] = None
    else:
        value = response.pop('ChartType')
        response['InfoViewChartType'] = textToValueDict[value] if value else None

def replaceWithProperTag(tag):
    return closest_match(tag,retrieved_tag_names,scorerType=1)[0]

def getTagDetails(tags):
    stringified_tags = ','.join(tags)
    search_tags = urllib.parse.quote_plus(stringified_tags)
    tag_detail_search_url = TAG_DETAIL_SEARCH_API_PREFIX + search_tags
    response_tag_detail = requests.get(tag_detail_search_url, headers=HEADERS)
    response_tag_detail = response_tag_detail.json()
    return response_tag_detail


def processTags(response):
    '''
    Do not use this function from main.py
    '''

    tags = [replaceWithProperTag(tag) for tag in response['Tags']]
    tagdetails = getTagDetails(tags)

    if response['MetricTypePerTag']:
        for tagdetail in tagdetails:
            for metric in response["MetricTypePerTag"]:
                score = closest_match(tagdetail['Name'],[metric['Tag']],scorerType=1)[1]
                if(score>70):
                    tagdetail['MetricName'] = metric['MetricName']
    
    tags = [f"{tagdetail['Name']} | {tagdetail['MetricName']} | {i}" for i, tagdetail in enumerate(tagdetails)]
    response['TagsNew'] = tags
    response['Tags'] = "'"+f"{','.join(tags)}"+"'"
    response['TagDetails'] = json.dumps(tagdetails)
    
    

def merge(response,infoViewSettings):
    '''
    Merges the processed AI output with the base infoViewSettings object
    returns modified infoViewSettings object
    '''
    for setting in infoViewSettings:
        if((setting not in response) or response[setting]==None):
            continue
        infoViewSettings[setting] = response[setting]


def processAIOutput(response,infoViewSettings):
    '''
    This function converts the AI generated response into useful values and merges them with infoViewSettings
    '''
    processRelativeTimeBase(response)
    processRelativeTimeMultiplier(response)
    processRelativeTimeIdentifier(response)
    processOperator(response)
    processIntervalValue(response)
    processIntervalType(response)
    processIntervalSpread(response)
    processInfoViewType(response)
    processGaugeType(response)
    processGaugeOrientation(response)
    processInfoViewChartType(response)
    processTags(response)
    merge(response,infoViewSettings)
    
    return infoViewSettings

