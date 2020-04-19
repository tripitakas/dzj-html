from . import api, view, task

views = [
    view.CharListHandler, view.CharBrowseHandler, view.CharStatHandler,
    task.CharTaskAdminHandler, task.CharTaskStatHandler, task.CharTaskClusterHandler,
]

handlers = [
    api.CharGenImgApi, api.CharUpdateApi, api.CharSourceApi,
    task.CharTaskPublishApi, task.CharTaskClusterApi,
]
