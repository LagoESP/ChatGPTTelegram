#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
import os
from datetime import time
from bs4 import BeautifulSoup
import openai
import flag
from github import Github, GithubException
from googletrans import Translator, LANGCODES, constants
import requests
import pycountry
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, Filters, MessageHandler
import unicodedata

FREECREDITS = 1000
OWNER = 'Lagortinez'
OWNERID = 298181113
OPENAITOKEN = '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'
GITTOKEN = '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'
TOKEN = '5737978785:AAHXCAal-gikyL-nBmU8feAp3Xn_LA3kVtY'
translator = Translator()

openai.api_key = OPENAITOKEN

github = Github(GITTOKEN)
REPO = github.get_user().get_repo('ChatGPTTelegram')
fileRoute = 'Files/'

MODE, TITLE, NAME, LANG, GETUSERSCREDIT, SETCREDITS, YESNO, TEMPLATE = range(8)

# Functions


def writeFile_GH(fileName, fileContent):
    try:
        REPO.create_file(fileRoute + fileName, 'Creating ' +
                         fileName, content=str(fileContent))
    except GithubException as g:
        if g.data['message'] == "Invalid request.\n\n\"sha\" wasn't supplied.":
            file = REPO.get_contents(fileRoute + fileName)
            REPO.update_file(file.path, 'Updating ' +
                             fileName, str(fileContent), file.sha)
        else:
            print(g)


def readFile_GH(fileName):
    file = REPO.get_contents(fileRoute + fileName)
    try:
        return ast.literal_eval(file.decoded_content.decode())
    except:
        return file.decoded_content.decode()


def removeFile_GH(fileName):
    file = REPO.get_contents(fileRoute + fileName)
    REPO.delete_file(file.path, 'Deleting ' + fileName, file.sha)


def isfile_GH(fileName):
    try:
        REPO.get_contents(fileRoute + fileName)
    except GithubException as g:
        if g.data['message'] == 'Not Found':
            return False
        else:
            print(g)
    return True


def get_files_GH(route):
    return [f.name for f in REPO.get_contents(route)]


def getWhiteListBool(update: Update):
    if not isfile_GH('whitelist.txt'):
        return False
    whiteList = readFile_GH('whitelist.txt')
    if (update.message.chat.type == 'private'):
        for auth in whiteList:
            if auth['userName'] == update.message.from_user.name:
                return True
    return False


def if_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def isUser(update: Update, user: str):
    return '@' + user == (update.message.from_user.name)


def registerUnauthUsers(update: Update, context: CallbackContext):
    if not isfile_GH('unregisteredUsers.txt'):
        writeFile_GH('unregisteredUsers.txt', [])
        writeFile_GH('unregisteredUsersChatID.txt', [])
    unregisteredUsers = readFile_GH('unregisteredUsers.txt')
    if update.message.from_user.name not in unregisteredUsers:
        unregisteredUsers.append(update.message.from_user.name)
        writeFile_GH('unregisteredUsers.txt', unregisteredUsers)
        unregisteredUsersChatID = readFile_GH('unregisteredUsersChatID.txt')
        unregisteredUsersChatID.append(
            {'name': update.message.from_user.name, 'chatID': update.message.chat.id})
        writeFile_GH('unregisteredUsersChatID.txt', unregisteredUsersChatID)
    context.bot.send_message(chat_id=update.message.chat.id, text=translate(
        f'Uso no autorizado, se ha registrado su intento de uso. Si desea ser autorizado, contacte con @{OWNER}', update.message.from_user.language_code))
    context.bot.send_message(
        chat_id=OWNERID, text=f'Attempt of unauthorised usage from {update.message.from_user.name}')


def getUnauthorizedUsers(update: Update, context: CallbackContext):
    unregisteredUsersChatID = readFile_GH('unregisteredUsersChatID.txt')
    if isUser(update, OWNER):
        for user in unregisteredUsersChatID:
            context.bot.send_message(
                chat_id=update.message.chat.id, text=f'User: {user["name"]}, ChatID: {user["chatID"]}')


def getConversationHistory(user: str):
    if isfile_GH(user+'_ConversationHistory.txt'):
        userData = readFile_GH(user+'_ConversationHistory.txt')
        return userData['conversationHistory']
    else:
        return []


def updateConversationHistory(user: str, conversationHistory: list):
    writeFile_GH(user+'_ConversationHistory.txt', conversationHistory)


def clearConversationHistory(user: str):
    updateConversationHistory(user, [])


def startChatGPTCall(prompt: str, conversationHistory: list = []):
    message = []
    for element in conversationHistory:
        message.append(element)
    message.append({"role": "user", "content": prompt})
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message
    )

    result = ''
    for choice in completion.choices:
        result += choice.message.content

    message.append({"role": "assistant", "content": result})
    return result, message, completion.usage.total_tokens


def chatting(update: Update, context: CallbackContext):
    if (getWhiteListBool(update) and OWNERID == update.message.chat.id):
        isFile = isfile_GH(
            update.message.from_user.name+'_ConversationHistory.txt')
        conversationHistory = []
        if (isFile):
            conversationHistory = readFile_GH(
                update.message.from_user.name+'_ConversationHistory.txt')
        response, conversationHistory, tokens = startChatGPTCall(
            update.message.text, conversationHistory)
        update.message.reply_text(response)
        update.message.reply_text(f'Used {tokens} tokens')
        updateConversationHistory(
            update.message.from_user.name, conversationHistory)


def flush(update: Update, context: CallbackContext):
    if (getWhiteListBool(update) and OWNERID == update.message.chat.id):
        clearConversationHistory(update.message.from_user.name)
        update.message.reply_text('Conversation history flushed')


def template(update: Update, context: CallbackContext):
    if (getWhiteListBool(update) and OWNERID == update.message.chat.id):
        isFile = isfile_GH(
            update.message.from_user.name+'_template.txt')
        if (isFile):
            template = readFile_GH(
                update.message.from_user.name+'_template.txt')
            update.message.reply_text(
                translate('Actualmente tienes esta plantilla:', update.message.from_user.language_code))
            update.message.reply_text(template)
            keyboard = [[InlineKeyboardButton(translate("Yes", update.message.from_user.language_code), callback_data='yes'),
                         InlineKeyboardButton(translate("No", update.message.from_user.language_code), callback_data='no')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                translate('¿Quieres cambiarla?', update.message.from_user.language_code), reply_markup=reply_markup)
            return YESNO
        else:
            keyboard = [[InlineKeyboardButton(translate("Yes", update.message.from_user.language_code), callback_data='yes'),
                         InlineKeyboardButton(translate("No", update.message.from_user.language_code), callback_data='no')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                translate('Ahora mismo no tienes ninguna plantilla. ¿Quieres añadir una ahora?', update.message.from_user.language_code), reply_markup=reply_markup)
            return YESNO


def templateYesNo(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    userData = readFile_GH(query.from_user.name +
                           '.txt')

    if query.data == 'yes':
        query.edit_message_text(
            translate('Perfecto. Envíame la plantilla que quieres usar.', userData['lang']))
        return TEMPLATE
    else:
        query.edit_message_text(
            translate('¡Sin problema!', userData['lang']))
        return ConversationHandler.END


def updateTemplate(update: Update, context: CallbackContext):
    if (getWhiteListBool(update)):
        userData = readFile_GH(update.message.from_user.name +
                               '.txt')
        writeFile_GH(update.message.from_user.name +
                     '_template.txt', update.message.text)
        update.message.reply_text(
            translate('Plantilla actualizada correctamente', userData['lang']))
        return ConversationHandler.END


def deleteTemplate(update: Update, context: CallbackContext):
    if (getWhiteListBool(update)):
        if isfile_GH(update.message.from_user.name+'_template.txt'):
            removeFile_GH(update.message.from_user.name+'_template.txt')
            update.message.reply_text(
                translate('Plantilla eliminada correctamente', update.message.from_user.language_code))
            return ConversationHandler.END
        else:
            update.message.reply_text(
                translate('No tienes ninguna plantilla guardada', update.message.from_user.language_code))
            return ConversationHandler.END


def start(update: Update, context: CallbackContext):
    if (getWhiteListBool(update)):
        isFile = isfile_GH(
            update.message.from_user.name+'.txt')
        if (isFile):
            userData = readFile_GH(update.message.from_user.name+'.txt')
            update.message.reply_text(
                translate('¡Hola! Necesitaré el título del artículo a reseñar. Puedes enviarme el link de Amazon si tienes dudas.', userData['lang']))
            return TITLE
        else:
            if update.message.from_user.language_code == 'en':
                language = 'us'
            else:
                language = update.message.from_user.language_code
            update.message.reply_text(
                translate(f'Primera vez por aquí... Déjame ayudarte. Voy a crearte un registro de uso. Con ello tendremos registrado el número de usos que haces contra la IA. También he detectado que tu idioma es {flag.flag(language)}. Si no es así, cámbialo con /language.', update.message.from_user.language_code))
            writeFile_GH(update.message.from_user.name +
                         '.txt', {'usedTokens': 0, 'ownedTokens': int(FREECREDITS)*2, 'lang': update.message.from_user.language_code, 'chatID': update.message.from_user.id})
            update.message.reply_text(
                translate(f'Registro creado. Se te han añadido {int(FREECREDITS)*2} Créditos para que puedas probar el bot de manera gratuita. Te recomendaría que me pidieses ayuda con /help para charlar acerca de lo que puedo hacer por tí. ¡Envía /start para empezar a generar reseñas!', update.message.from_user.language_code))
        return ConversationHandler.END
    else:
        registerUnauthUsers(update, context)
        return ConversationHandler.END


def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    userData = readFile_GH(query.from_user.name +
                           '.txt')
    score = query.data
    if score == '0':
        query.edit_message_text(text=translate(
            "Reseña cancelada. Envía /start para empezar de nuevo.", userData['lang']))
        return ConversationHandler.END

    if userData['ownedTokens'] <= 500:
        query.edit_message_text(
            text=translate(f'No tienes Créditos suficientes para hacer una reseña (mínimo 500, tienes {userData["ownedTokens"]})... Recarga Créditos contactando con @{OWNER}!', userData['lang']))
        return ConversationHandler.END
    else:
        if isfile_GH(f'{query.from_user.name}_template.txt'):
            template = readFile_GH(
                f'{query.from_user.name}_template.txt')
        else:
            template = None
        query.edit_message_text(
            text=translate(f'Generando reseña sin plantilla', userData['lang']))

        result = logic(Title, int(score), userData["lang"], template)
        query.bot.send_message(chat_id=update.effective_chat.id,
                               text=translate(result['text'], userData['lang']))
        query.bot.send_message(chat_id=update.effective_chat.id,
                               text=translate('Para solicitar otra reseña, envía /start.', userData['lang']))
        userData = readFile_GH(query.from_user.name +
                               '.txt')
        userData['usedTokens'] += result['usedTokens']
        userData['ownedTokens'] -= result['usedTokens']
        writeFile_GH(query.from_user.name + '.txt', userData)
    return ConversationHandler.END


def extractItemTitleFromAmazonUrl(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find(id="productTitle").get_text().strip()
        return title
    except:
        return False


def title(update: Update, context: CallbackContext):
    if (update.message.text == '/help'):
        help(update, context)
    elif (update.message.text == '/cancel'):
        cancel(update, context)
    else:
        userData = readFile_GH(update.message.from_user.name+'.txt')
        global Title
        if update.message.text.__contains__("www.amazon"):
            Title = extractItemTitleFromAmazonUrl(update.message.text)
            if Title == False:
                update.message.reply_text(
                    translate('No he podido extraer el título del artículo. Por favor, envíame el título del artículo a reseñar.', userData['lang']))
                return TITLE
        else:
            Title = update.message.text
        keyboard = [
            [
                InlineKeyboardButton(
                    "⭐", callback_data='1'),
            ],
            [
                InlineKeyboardButton(
                    "⭐⭐", callback_data='2'),
            ],
            [
                InlineKeyboardButton(
                    "⭐⭐⭐", callback_data='3'),
            ],
            [
                InlineKeyboardButton(
                    "⭐⭐⭐⭐", callback_data='4'),
            ],
            [
                InlineKeyboardButton(
                    "⭐⭐⭐⭐⭐", callback_data='5'),
            ],
            [
                InlineKeyboardButton(
                    "Cancelar", callback_data="0"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            translate('Por favor, elije la puntuación de tu reseña:', userData['lang']), reply_markup=reply_markup)
        return MODE
    return ConversationHandler.END


def translate(text: str, lang: LANGCODES) -> str:
    return translator.translate(text, dest=lang).text


def logic(title: str, rating: int, language: str, template: str = None) -> dict:
    prompt = f"Write a customer review with the purpose of publishing it on Amazon. The review has to be the closest to a Amazon Vine review/profesional review that you a customer would enjoy reading. The title of the item is {title} and the rating is {rating}/5 stars. You must not repeat the title more than once in the review. The review length must be at least 200 words. The output has to be in {pycountry.languages.get(alpha_2=language).name}."
    if template != None:
        prompt += f" Moreover, you have to follow this template: {template}"
    result, message, usedToken = startChatGPTCall(prompt)
    return {"text": result, "usedTokens": usedToken}


def language(update: Update, context: CallbackContext):
    if (getWhiteListBool(update)):
        isFile = isfile_GH(
            update.message.from_user.name+'.txt')
        if (isFile):
            userData = readFile_GH(update.message.from_user.name+'.txt')
            keyboard = [
                [
                    InlineKeyboardButton(flag.flag('US'), callback_data='en'),
                    InlineKeyboardButton(flag.flag('ES'), callback_data='es'),
                    InlineKeyboardButton(flag.flag('DE'), callback_data='de'),
                ],
                [
                    InlineKeyboardButton(flag.flag('IT'), callback_data='it'),
                    InlineKeyboardButton(flag.flag('FR'), callback_data='fr'),
                    InlineKeyboardButton(flag.flag('PT'), callback_data='pt'),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                translate('Por favor, elije el modo de generación de reseñas:', userData['lang']), reply_markup=reply_markup)
            return LANG
        else:
            update.message.reply_text(
                translate('No tienes registro creado. Crea uno usando /start y luego podrás cambiar el idioma del bot.', update.message.from_user.language_code))
    return ConversationHandler.END


def langSet(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    userData = readFile_GH(query.from_user.name +
                           '.txt')

    userData['lang'] = query.data
    writeFile_GH(query.from_user.name + '.txt', userData)
    query.edit_message_text(
        text=translate(f'Great! Now on all the content will be generated in {str.capitalize(constants.LANGUAGES[query.data])}.', userData['lang']))
    return ConversationHandler.END


def help(update: Update, context: CallbackContext):
    if (getWhiteListBool(update)):
        isFile = isfile_GH(update.message.from_user.name+'.txt')
        if (isFile):
            lang = readFile_GH(
                update.message.from_user.name + '.txt')['lang']
        else:
            lang = update.message.from_user.language_code
        update.message.reply_text(translate(
            'Welcome to help mode. Here you can find help regarding this Review Generation Tool.', lang))
        update.message.reply_text(translate(
            'This tool creates unique reviews using advanced AI in order to help you reviewing anything that you might need.', lang))
        update.message.reply_text(translate(
            'To run the tool, you just have to press /start and I will ask you for a title of the review. Try to be as accurate as possible (Eg: Samsung FreeBuds or Set of 12 socks for man, black colour.)', lang))
        update.message.reply_text(translate(
            'When I get the title, I will ask you about the text mode. You will have 2 options:', lang))
        update.message.reply_text(translate('Article Mode: If you gave me enough data, I will try to generate a proffesinal review about the item you specified, getting into details as much as possible. If you made a typo while texting me, this result might be innacurate or if the item is too common, the review would not be as expected. Depends on the information provided, the review size might vary, but on average is around 300 words.', lang))
        update.message.reply_text(translate(
            'Review Mode: I will give you a short generic review with the information that you gave me. This review is usually around 30-80 words. Works nicely for generic items.', lang))
        update.message.reply_text(translate(
            'Each review will cost you a random amount of credit. You can expect around 100 Credits with the Review Mode up to 600 Credits.', lang))
        update.message.reply_text(translate(
            f'You must to have in your account at least 100 credits to generate a review. For topping up your account contact @{OWNER}.', lang))
        update.message.reply_text(translate('Enjoy Reviewing!', lang))
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    if (getWhiteListBool(update)):
        isFile = isfile_GH(update.message.from_user.name+'.txt')
        if (isFile):
            lang = readFile_GH(
                update.message.from_user.name + '.txt')['lang']
        else:
            lang = update.message.from_user.language_code
        update.message.reply_text(translate('See you later!', lang))
    return ConversationHandler.END

# Credit Tools


def getCredits(update: Update, context: CallbackContext):
    if (getWhiteListBool(update)):
        isFile = isfile_GH(
            update.message.from_user.name+'.txt')
        if (isFile):
            userData = readFile_GH(update.message.from_user.name+'.txt')
            update.message.reply_text(translate(
                f'Your current balance is {userData["ownedTokens"]} credits.', userData['lang']))
        else:
            update.message.reply_text(translate(
                'You are not registered yet! Try /start and try me for free.', update.message.from_user.language_code))


def topUpCredits(update: Update, context: CallbackContext):
    if (isUser(update, OWNER
               )):
        update.message.reply_text(translate(
            'Introduce el usuario el cual quieras modificar fondos.', update.message.from_user.language_code))
        return SETCREDITS


def getUsersCredit(update: Update, context: CallbackContext):
    isFile = isfile_GH(f"{update.message.text}.txt")
    if (isFile):
        global userToAdd
        userToAdd = update.message.text
        userData = readFile_GH(f"{update.message.text}.txt")
        update.message.reply_text(translate(
            f'Usuario encontrado. Balance actual de {userData["ownedTokens"]}. Introduce la cantidad (en miles) de Créditos a añadir. /cancel para salir.', update.message.from_user.language_code))
        return GETUSERSCREDIT
    else:
        update.message.reply_text(translate(
            'El usuario especificado no está registrado. No ha habido cambios.', update.message.from_user.language_code))
        return ConversationHandler.END


def setCredits(update: Update, context: CallbackContext):
    if if_float(update.message.text):
        userData = readFile_GH(userToAdd+'.txt')
        userData['ownedTokens'] += float(update.message.text)*1000
        writeFile_GH(userToAdd+'.txt', userData)
        update.message.reply_text(translate(
            f'Saldo añadido. Nuevo saldo {userData["ownedTokens"]} créditos. Cambios guardados.', update.message.from_user.language_code))
        return ConversationHandler.END
    elif update.message.text == '/cancel':
        update.message.reply_text(translate(
            'No ha habido cambios. Saliendo.', update.message.from_user.language_code))
        return ConversationHandler.END
    else:
        update.message.reply_text(translate(
            'No se ha detectado número. Prueba otra vez o /cancel', update.message.from_user.language_code))


# WhiteList Tools

def listWhitelistCommand(update: Update, context: CallbackContext):
    if (isUser(update, OWNER
               )):
        isFile = isfile_GH("whitelist.txt")
        if (isFile):
            list = readFile_GH("whitelist.txt")
            if (list == []):
                update.message.reply_text(translate(
                    'No hay whitelist. Agrega una con /whitelistUpdate', update.message.from_user.language_code))
            for user in list:
                update.message.reply_text(
                    f'{user["userName"]}')
        else:
            update.message.reply_text(
                translate('Creating Whitelist...', update.message.from_user.language_code))
            writeFile_GH("whitelist.txt", [])
            update.message.reply_text(translate(
                '¡Whitelist creada! Necesitaré que me indiques que cuentas quieres que compruebe. Házmelo saber con /whitelistUpdate', update.message.from_user.language_code))


def updateWLCommand(update: Update, context: CallbackContext):
    if (isUser(update, OWNER)):
        isFile = isfile_GH("whitelist.txt")
        if (isFile):
            update.message.reply_text(translate(
                'Introduce el nombre de la persona que quieras agregar a la whitelist', update.message.from_user.language_code))
            return NAME
        else:
            update.message.reply_text(translate(
                'Creating whitelist...', update.message.from_user.language_code))
            writeFile_GH("whitelist.txt", [])
            update.message.reply_text(translate(
                '¡Whitelist creada! Necesitaré que me indiques que cuentas quieres que compruebe. Házmelo saber con /whitelistUpdate', update.message.from_user.language_code))
            return ConversationHandler.END


def isUserBenefit(update: Update, context: CallbackContext):
    if (update.message.text == '/cancel'):
        update.message.reply_text('Chao!')
        return ConversationHandler.END
    global userName
    userName = update.message.text
    keyboard = [
        [
            InlineKeyboardButton(
                translate('Yes', update.message.from_user.language_code), callback_data='1'),
            InlineKeyboardButton(
                translate('No', update.message.from_user.language_code), callback_data='0'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(translate(f'¿Es {userName} miembro del canal? (Cada mes se le renovarán {FREECREDITS} créditos gratis)',
                              update.message.from_user.language_code), reply_markup=reply_markup)
    return YESNO


def updateWL(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    oldList = readFile_GH('whitelist.txt')
    for user in oldList:
        if (user == userName):
            update.message.reply_text(translate(
                f'{userName} ya se encuentra en la whitelist. No se ha agregado nada.', update.message.from_user.language_code))
            return ConversationHandler.END
    oldList.append({'userName': userName})
    writeFile_GH('whitelist.txt', oldList)
    query.edit_message_text(translate(f'{userName} se ha agregado correctamente.',
                                      query.from_user.language_code))
    return ConversationHandler.END


def deleteWLCommand(update: Update, context: CallbackContext):
    if (isUser(update, OWNER
               )):
        isFile = isfile_GH("whitelist.txt")
        if (isFile):
            update.message.reply_text(translate(
                'Introduce el nombre de la persona que quieras eliminar de la whitelist', update.message.from_user.language_code))
            return NAME
        else:
            update.message.reply_text(translate(
                'No hay whitelist. Creando whitelist...', update.message.from_user.language_code))
            writeFile_GH("whitelist.txt", [])
            update.message.reply_text(translate(
                '¡Whitelist creada! Necesitaré que me indiques que cuentas quieres que compruebe. Házmelo saber con /whitelistUpdate', update.message.from_user.language_code))
            return ConversationHandler.END


def deleteWL(update: Update, context: CallbackContext):
    if (update.message.text == '/cancel'):
        update.message.reply_text('Chao!')
        return ConversationHandler.END
    oldList = readFile_GH("whitelist.txt")
    i = 0
    for user in oldList:
        if (user['userName'] == update.message.text):
            oldList.pop(i)
            update.message.reply_text(translate(
                update.message.text + " ha sido correctamente eliminado.", update.message.from_user.language_code))
            writeFile_GH("whitelist.txt", oldList)
            return ConversationHandler.END
        i += 1
    update.message.reply_text(translate("No se ha encontrado al usuario " +
                              update.message.text + " en la whitelist. No se ha modificado nada.", update.message.from_user.language_code))
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        MODE: [CallbackQueryHandler(button)],
        TITLE: [MessageHandler(Filters.text, title)],
    },
    fallbacks=[CommandHandler('help', help),
               CommandHandler('cancel', cancel), ],
)

lang_handler = ConversationHandler(
    entry_points=[CommandHandler('language', language)],
    states={
        LANG: [CallbackQueryHandler(langSet)],
    },
    fallbacks=[CommandHandler('help', help),
               CommandHandler('cancel', cancel), ],
)

credit_handler = ConversationHandler(
    entry_points=[CommandHandler('setcredits', topUpCredits)],
    states={
        SETCREDITS: [MessageHandler(Filters.text, getUsersCredit)],
        GETUSERSCREDIT: [MessageHandler(Filters.text, setCredits)],
    },
    fallbacks=[CommandHandler('help', help),
               CommandHandler('cancel', cancel), ],
)


updtWL_handler = ConversationHandler(
    entry_points=[CommandHandler('whitelistupdate', updateWLCommand)],
    states={
        NAME: [MessageHandler(Filters.text, isUserBenefit)],
        YESNO: [CallbackQueryHandler(updateWL)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

delWL_handler = ConversationHandler(
    entry_points=[CommandHandler('whitelistdelete', deleteWLCommand)],
    states={
        NAME: [MessageHandler(Filters.text, deleteWL)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

flush_handler = ConversationHandler(
    entry_points=[CommandHandler('flush', flush)],
    states={
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

template_handler = ConversationHandler(
    entry_points=[CommandHandler('template', template)],
    states={
        YESNO: [CallbackQueryHandler(templateYesNo)],
        TEMPLATE: [MessageHandler(Filters.text, updateTemplate)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)


def main():
    '''Start the bot.'''

    updater = Updater(TOKEN)

    dp = updater.dispatcher

    dp.add_handler(updtWL_handler)
    dp.add_handler(delWL_handler)
    dp.add_handler(conv_handler)
    dp.add_handler(lang_handler)
    dp.add_handler(credit_handler)
    dp.add_handler(flush_handler)
    dp.add_handler(template_handler)
    dp.add_handler(CommandHandler('cancel', cancel))
    dp.add_handler(CommandHandler('deleteTemplate', deleteTemplate))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler("getcredits", getCredits))
    dp.add_handler(CommandHandler(
        "getUnauthorizedUsers", getUnauthorizedUsers))
    dp.add_handler(CommandHandler(
        "listwhitelist", listWhitelistCommand))
    dp.add_handler(MessageHandler(Filters.text, chatting))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()