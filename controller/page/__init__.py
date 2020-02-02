from . import api, view

views = [
    view.CutTaskHandler, view.CutEditHandler,
    view.TextProofHandler, view.TextReviewHandler, view.TextEditHandler,
]

handlers = [
    api.CutTaskApi, api.CutEditApi, api.GenCharIdApi,
    api.SelectTextApi, api.NeighborTextApi,
    api.TextProofApi, api.TextReviewApi, api.TextHardApi, api.TextEditApi,
    api.FetchDataTasksApi, api.SubmitDataTasksApi, api.ConfirmFetchDataTasksApi,
]

modules = {'TextArea': view.TextArea}
