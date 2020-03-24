from . import api, view

views = [
    view.CharBrowseHandler, view.TaskCharClusterHandler,
]

handlers = [
    api.CharGenImgApi, api.CharUpdateApi, api.PublishCharTasksApi, api.UpdateCharSourceApi,
    api.TaskCharClusterProofApi,
]
