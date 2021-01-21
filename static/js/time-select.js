/**
 * 检索时的时间设置
 */

// bootstrap modal with select2 focus
$.fn.modal.Constructor.prototype.enforceFocus = function () {
};

let tStatus = {start: '.finished_start', end: '.finished_end'};
$('.picked_time input').on('click', () => Object.assign(tStatus, {start: '.picked_start', end: '.picked_end'}));
$('.publish_time input').on('click', () => Object.assign(tStatus, {start: '.publish_start', end: '.publish_end'}));
$('.finished_time input').on('click', () => Object.assign(tStatus, {start: '.finished_start', end: '.finished_end'}));
// 时间设置
$('input.flatpickr').flatpickr({allowInput: true, defaultHour: 0, locale: 'zh', time_24hr: true});
$('#clear').on('click', () => $('input.flatpickr').val(''));
$('#last-week').on('click', function () {
  let start = new Date();
  let day = start.getDay() || 7;
  start.setDate(start.getDate() - day - 7);
  start = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  $(tStatus.start).val(start.format("yyyy-MM-dd hh:mm:ss"));
  let end = new Date();
  end.setDate(end.getDate() - day - 1);
  end = new Date(end.getFullYear(), end.getMonth(), end.getDate(), 23, 59, 59);
  $(tStatus.end).val(end.format("yyyy-MM-dd hh:mm:ss"));
});

$('#this-week').on('click', function () {
  let date = new Date();
  let day = date.getDay() || 7;
  date.setDate(date.getDate() - day + 1);
  date = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  $(tStatus.start).val(date.format("yyyy-MM-dd hh:mm:ss"));
  $(tStatus.end).val("");
});

$('#this-month').on('click', function () {
  let date = new Date();
  date = new Date(date.getFullYear(), date.getMonth());
  $(tStatus.start).val(date.format("yyyy-MM-dd hh:mm:ss"));
  $(tStatus.end).val("");
});

$('#last-month').on('click', function () {
  let date = new Date();
  let start = new Date(date.getFullYear(), date.getMonth() - 1);
  if (date.getMonth() == 1) start = new Date(date.getFullYear() - 1, 12);
  $(tStatus.start).val(start.format("yyyy-MM-dd 00:00:00"));
  let end = new Date(date.getFullYear(), date.getMonth());
  $(tStatus.end).val(end.format("yyyy-MM-dd 00:00:00"));
});

