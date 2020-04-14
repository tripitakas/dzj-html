from . import api, view

views = [
    view.TaskInfoHandler, view.TaskSampleHandler,
]

handlers = [
    api.PickTaskApi, api.ReturnTaskApi, api.UpdateTaskApi, api.RepublishTaskApi,
    api.DeleteTasksApi, api.AssignTasksApi, api.FinishTaskApi,
]
