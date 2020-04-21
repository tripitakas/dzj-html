from . import api, view

views = [
    view.CharListHandler, view.CharBrowseHandler, view.CharStatHandler, view.CharViewHandler,
    view.CharTaskAdminHandler, view.CharTaskStatHandler, view.CharTaskClusterHandler,
]

handlers = [
    api.CharGenImgApi, api.CharUpdateApi, api.CharSourceApi,
    api.CharTaskPublishApi, api.CharTaskClusterApi,
]
