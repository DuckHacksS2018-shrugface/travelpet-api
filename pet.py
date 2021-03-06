import time
import datetime
import random

import connexion
from pymongo import MongoClient

client = MongoClient("mongodb+srv://admin:shrugface@petuserdata-vckb7.mongodb.net/test")
db = client.data

def update_everything(petID):
    """
    Things to update:
        * age
        cleanliness
        discipline
        happiness
        hunger
        * meals_used
        * poo
        sick
        * asleep
        weight
    """
    curState = db.pet.find_one({'petID': petID})
    curTime = time.time()
    curDateTime = datetime.datetime()
    timeSinceInter = curTime - curState['last_interaction']
    # Whether it died
    if curState['age'] < 0:
        return False
    if timeSinceInter > 172800:  # More than a week since interaction
        db.pet.update_one({'petID': petID}, {'$set': {'age': -1}})
        return False
    if curTime - curState['spawned'] > 1728000:
        db.pet.update_one({'petID': petID}, {'$set': {'age': -1}})
        return False
    # Whether it can eat meals
    if curTime - curState['last_meal'] > 86400:  # One day has passed since food
        db.pet.update_one({'petID': petID}, {'$set': {'meals_used': 0}})
    # Whether it's hatched
    if curState['age'] == 0 and curTime - curState['spawned'] < curState['hatch_time']:
        db.pet.update_one({'petID': petID}, {'$set': {'age': 1}})
    # Whether it's asleep
    if curDateTime.hour > 21 and curDateTime.hour < 8:
        db.pet.update_one({'petID': petID}, {'$set': {'asleep': True}})
    else:
        db.pet.update_one({'petID': petID}, {'$set': {'asleep': False}})
    # Poo
    if curTime - curState['last_cleaned'] > 3600:
        if curState['last_poo'] and curTime - curState['last_poo'] > 600:
            if random.randint(0,1):
                db.pet.update_one({'petID': petID}, {'$inc': {'poo': 1}})
                db.pet.update_one({'petID': petID}, {'$set': {'last_poo': time.time()}})
    return True

def get_data(petID):
    if not update_everything(petID):
        return {'result': 'Your pet is dead'}, 400, {'Access-Control-Allow-Origin': '*'}
    result = db.pet.find_one({'petID': petID})
    if result == None:
        return {'result': 'Pet not found'}, 404, {'Access-Control-Allow-Origin': '*'}
    rDict = {}
    for key, val in result.items():
        rDict[key] = val
    rDict.pop('_id')
    return rDict, 200, {'Access-Control-Allow-Origin': '*'}

def make_new(petID):
    args = connexion.request.args
    username = args.get('username')
    petname = args.get('petname')
    if db.pet.find_one({'petID': petID}) != None:
        return {'result': 'Pet with ID already exists'}, 409, {'Access-Control-Allow-Origin': '*'}
    if db.user.find_one({'user': username}) == None:
        return {'result': 'That user does not exist'}, 400, {'Access-Control-Allow-Origin': '*'}
    new_pet = {
        'petID': petID,
        'name': petname,
        'ownername': username,
        'hunger': 5,
        'happiness': 5,
        'discipline': 5,
        'cleanliness': 5,
        'sick': False,
        'age': 0,
        'weight': 5,
        'poo': 5,
        'asleep': False,
        'last_interaction': time.time(),
        'last_meal': time.time(),
        'last_fed': time.time(),
        'last_poo': None,
        'last_cleaned': time.time(),
        'last_washed': time.time(),
        'last_disciplined': time.time(),
        'spawned': time.time(),
        'hatch_time': 30 + random.randint(0,60),
        'meals_used': 0
    }
    db.pet.insert_one(new_pet)
    petslist = db.user.find_one({'user': username})['pets']
    petslist.append(petID)
    db.user.update_one({'user': username}, {'$set': {'pets': petslist}})
    return {'result': 'made a pet', 'id': petID}, 200, {'Access-Control-Allow-Origin': '*'}

def delete(petID):
    args = connexion.request.args
    username = args.get('username')
    uresult = db.user.find_one({'user': username})
    if uresult == None:
        return {'result': 'That user does not exist'}, 400, {'Access-Control-Allow-Origin': '*'}
    petslist = uresult['pets']
    if not petID in petslist:
        return {'result': 'That user does not own that pet'}, 404, {'Access-Control-Allow-Origin': '*'}
    petslist.remove(petID)
    db.user.update_one({'user': username}, {'$set': {'pets': petslist}})
    result = db.pet.delete_one({'petID': petID})
    if result.deleted_count == 1:
        return {'result': 'Killed pet'}, 200, {'Access-Control-Allow-Origin': '*'}
    return {'result': 'Could not delete pet'}, 500, {'Access-Control-Allow-Origin': '*'}

def feed(petID, foodID):
    if not update_everything(petID):
        return {'result': 'Your pet is dead'}, 400, {'Access-Control-Allow-Origin': '*'}
    foodData = db.food.find_one({'foodID': foodID})
    if foodData == None:
        return {'result': 'No such food'}, 404, {'Access-Control-Allow-Origin': '*'}
    fillingLevel = foodData['filling']
    meal = foodData['meal']
    if meal:
        if db.pet.find_one({'petID': petID})['meals_used'] < 5:
            db.pet.update_one({'petID': petID}, {'$inc': {'meals_used': 1}})
            db.pet.update_one({'petID': petID}, {'$set': {'last_meal': time.time()}})
        else:
            return {'result': 'Your pet is full'}, 400, {'Access-Control-Allow-Origin': '*'}
    curFilled = db.pet.find_one({'petID': petID})['hunger']
    newFilled = curFilled + fillingLevel
    if newFilled > 5:
        newFilled = 5
    db.pet.update_one({'petID': petID}, {'$set': {'hunger': newFilled, 'last_fed': time.time(), 'last_interaction': time.time()}})
    return {'result': 'Pet fed', 'hunger': newFilled}, 200, {'Access-Control-Allow-Origin': '*'}

def play(petID, gameID):
    if not update_everything(petID):
        return {'result': 'Your pet is dead'}, 400, {'Access-Control-Allow-Origin': '*'}
    result = db.pet.find_one({'petID': petID})
    if result['hunger'] < 1:
        return {'result': 'Your pet is too hungry to play'}, 400, {'Access-Control-Allow-Origin': '*'}
    if result['happiness'] > 3:
        db.pet.update_one({'petID': petID}, {'$set': {'happiness': 5}})
    else:
        db.pet.update_one({'petID': petID}, {'$inc': {'happiness': 2}})
    db.pet.update_one({'petID': petID}, {'$inc': {'hunger': -1}})
    db.pet.update_one({'petID': petID}, {'$set': {'last_interaction': time.time()}})
    return {'result': 'Played with pet'}, 200, {'Access-Control-Allow-Origin': '*'}

def clean(petID):
    if not update_everything(petID):
        return {'result': 'Your pet is dead'}, 400, {'Access-Control-Allow-Origin': '*'}
    if db.pet.find_one({'petID': petID})['poo'] == 0:
        return {'result': 'No poo to clean up'}, 400, {'Access-Control-Allow-Origin': '*'}
    db.pet.update_one({'petID': petID}, {'$set': {'last_cleaned': time.time()}})
    db.pet.update_one({'petID': petID}, {'$set': {'poo': 0, 'last_poo': None, 'last_interaction': time.time()}})
    return {'result': 'Cleaned up poo'}, 200, {'Access-Control-Allow-Origin': '*'}

def wash(petID):
    if not update_everything(petID):
        return {'result': 'Your pet is dead'}, 400, {'Access-Control-Allow-Origin': '*'}
    if db.pet.find_one({'petID': petID})['cleanliness'] == 5:
        return {'result': "Your pet's already clean"}, 400, {'Access-Control-Allow-Origin': '*'}
    db.pet.update_one({'petID': petID}, {'$set': {'last_washed': time.time()}})
    db.pet.update_one({'petID': petID}, {'$set': {'cleanliness': 5, 'last_interaction': time.time()}})
    return {'result': 'Washed pet'}, 200, {'Access-Control-Allow-Origin': '*'}

def scold(petID):
    if not update_everything(petID):
        return {'result': 'Your pet is dead'}, 400, {'Access-Control-Allow-Origin': '*'}
    result = db.pet.find_one({'petID': petID})
    curDis = result['discipline']
    curHap = result['happiness']
    curDis += 1
    curHap -= 1
    if curDis > 5:
        return {'result': 'Pet is already at max discipline'}, 400, {'Access-Control-Allow-Origin': '*'}
    if curHap < 0:
        return {'result': 'Your pet is too unhappy to listen to you'}, 400, {'Access-Control-Allow-Origin': '*'}
    db.pet.update_one({'petID': petID}, {'$set': {'last_disciplined': time.time()}})
    db.pet.update_one({'petID': petID}, {'$set': {'discipline': curDis, 'happiness': curHap,
                                                  'last_interaction': time.time()}})
    return {'result': 'Disciplined pet'}, 200, {'Access-Control-Allow-Origin': '*'}

def heal(petID):
    if not update_everything(petID):
        return {'result': 'Your pet is dead'}, 400, {'Access-Control-Allow-Origin': '*'}
    if not db.pet.find_one({'petID': petID})['sick']:
        return {'result': 'Your pet is not sick'}, 400, {'Access-Control-Allow-Origin': '*'}
    db.pet.update_one({'petID': petID}, {'$set': {'sick': False, 'last_interaction': time.time()}})
    return {'result': 'Healed pet'}, 200, {'Access-Control-Allow-Origin': '*'}
