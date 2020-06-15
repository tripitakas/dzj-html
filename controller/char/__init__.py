from . import api, view

views = [
    view.CharListHandler, view.CharBrowseHandler, view.CharStatHandler, view.CharViewHandler,
    view.CharTaskListHandler, view.CharTaskStatHandler, view.CharTaskClusterHandler,
]

handlers = [
    api.CharDeleteApi, api.CharExtractImgApi, api.CharTxtApi, api.CharsTxtApi,
    api.CharSourceApi, api.CharTaskPublishApi, api.CharTaskClusterApi,
]
