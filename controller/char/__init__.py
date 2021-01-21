from . import api, view, api_task as at, view_task as vt

views = [
    view.CharListHandler, view.CharBrowseHandler, view.CharStatHandler, view.CharViewHandler,
    view.CharConsistentHandler, view.CharInfoHandler,
    vt.CharTaskListHandler, vt.CharTaskStatHandler, vt.CharTaskClusterHandler,
    vt.CharTaskDashBoardHandler,
]

handlers = [
    api.CharSourceApi, api.CharDeleteApi, api.CharTxtApi, api.CharsTxtApi, api.CharExtractImgApi,
    at.CharTaskPublishApi, at.CharTaskClusterApi,
]
