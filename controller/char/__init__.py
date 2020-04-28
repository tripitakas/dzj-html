from . import api, view

views = [
    view.CharListHandler, view.CharBrowseHandler, view.CharStatHandler, view.CharViewHandler,
    view.CharTaskListHandler, view.CharTaskStatHandler,
    view.CharTaskClusterHandler, view.CharTaskSeparateHandler,
]

handlers = [
    api.CharExtractImgApi, api.CharTxtApi, api.CharsTxtApi, api.CharBoxApi,
    api.CharSourceApi, api.CharTaskPublishApi, api.CharTaskClusterApi,
]
