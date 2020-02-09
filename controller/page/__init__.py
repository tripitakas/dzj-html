from . import api, ocr, view

views = [
    view.CutTaskHandler, view.CutEditHandler,
    view.TextProofHandler, view.TextReviewHandler, view.TextEditHandler,
]

handlers = [
    api.CutTaskApi, api.CutEditApi, api.GenCharIdApi, api.DetectWideCharsApi,
    api.SelectTextApi, api.NeighborTextApi,
    api.TextProofApi, api.TextReviewApi, api.TextHardApi, api.TextEditApi,
    ocr.FetchOcrTasksApi, ocr.SubmitOcrTasksApi, ocr.ConfirmFetchOcrTasksApi,
]

modules = {'TextArea': view.TextArea}
