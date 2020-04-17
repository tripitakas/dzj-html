from . import api, view

views = [
    view.CharBrowseHandler, view.CharBrowseHandler, view.CharStatHandler,
    view.CharTaskAdminHandler, view.CharTaskStatHandler,
    view.CharTaskLobbyHandler, view.CharTaskMyHandler, view.CharTaskClusterHandler,
]

handlers = [
    api.CharGenImgApi, api.CharUpdateApi, api.CharSourceApi,
    api.CharTaskPublishApi, api.CharTaskClusterApi,
]
