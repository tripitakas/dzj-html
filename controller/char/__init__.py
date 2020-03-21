from . import api, view

views = [
    view.CharBrowseHandler, view.TaskCharProofHandler,
]

handlers = [
    api.CharGenImgApi, api.CharUpdateApi, api.PublishCharTasksApi, api.UpdateCharBatchApi,
    api.TaskCharClusterProofApi,
]
