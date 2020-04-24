from . import api, view

views = [
    view.CharListHandler, view.CharBrowseHandler, view.CharStatHandler, view.CharViewHandler,
    view.CharTaskListHandler, view.CharTaskStatHandler,
    view.CharTaskClusterHandler, view.CharTaskSeparateHandler,
]

handlers = [
    api.CharGenImgApi, api.CharUpdateApi, api.CharSourceApi,
    api.CharTaskPublishApi, api.CharTaskClusterApi, api.CharTxtApi,
]
