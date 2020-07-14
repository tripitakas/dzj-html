from . import api, view, api_task as at, view_task as vt

views = [
    view.CharListHandler, view.CharBrowseHandler, view.CharStatHandler, view.CharViewHandler,
    vt.CharTaskListHandler, vt.CharTaskStatHandler, vt.CharTaskClusterHandler,
]

handlers = [
    api.CharSourceApi, api.CharDeleteApi, api.CharTxtApi, api.CharsTxtApi, api.CharExtractImgApi,
    at.CharTaskPublishApi, at.CharTaskClusterApi,
]
