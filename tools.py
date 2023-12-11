import configparser

def getSetting(settingName):
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    return config.get('Settings',settingName)

def setSetting(settingName, value):
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    config.set('Settings',settingName,value)
    with open('config.ini','w',encoding='utf-8')as file:
        config.write(file)