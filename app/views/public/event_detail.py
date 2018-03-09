import json
from datetime import datetime
import pytz

from flask import Blueprint
from flask import request, url_for, flash, escape, render_template, jsonify, make_response, current_app as app
from flask.ext import login
from flask.ext.restplus import abort
from markupsafe import Markup
from werkzeug.utils import redirect

from app.helpers.data import DataManager
from app.helpers.data_getter import DataGetter
from app.helpers.helpers import get_count
from app.models.call_for_papers import CallForPaper
from app.helpers.wizard.helpers import get_current_timezone
from app.settings import get_settings
from urllib2 import urlopen


def get_published_event_or_abort(identifier):
    event = DataGetter.get_event_by_identifier(identifier=identifier)
    if not event or event.state != u'Published':
        user = login.current_user
        if not login.current_user.is_authenticated or (not user.is_organizer(event.id) and not
           user.is_coorganizer(event.id) and not
                user.is_track_organizer(event.id)):

            abort(404)

    if event.deleted_at:
        abort(404)
    return event


event_detail = Blueprint('event_detail', __name__, url_prefix='/e')


@event_detail.route('/')
def display_default():
    return redirect("/browse/")


@event_detail.route('/<identifier>/')
def display_event_detail_home(identifier):
    event = get_published_event_or_abort(identifier)
    placeholder_images = DataGetter.get_event_default_images()
    if event.sub_topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
    elif event.topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
    else:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')

    call_for_speakers = DataGetter.get_call_for_papers(event.id).first()
    accepted_sessions = DataGetter.get_sessions(event.id).all()
    if event.copyright:
        licence_details = DataGetter.get_licence_details(event.copyright.licence)
    else:
        licence_details = None

    speakers = []
    for session in accepted_sessions:
        for speaker in session.speakers:
            if speaker not in speakers:
                speakers.append(speaker)

    '''Timezone aware current datetime object according to event timezone'''
    timenow_event_tz = datetime.now(pytz.timezone(event.timezone
                                                  if (event.timezone and event.timezone != '') else 'UTC'))
    module = DataGetter.get_module()
    tickets = DataGetter.get_sales_open_tickets(event.id, event.timezone
                                                  if (event.timezone and event.timezone != '') else 'UTC')
    sorted_tickets = sorted(tickets, key=lambda x: x['ticket'].position)

    '''Sponsor Levels'''
    sponsors = {-1: []}
    for sponsor in event.sponsor:
        if not sponsor.level:
            sponsors[-1].append(sponsor)
        elif int(sponsor.level) in sponsors.keys():
            sponsors[int(sponsor.level)].append(sponsor)
        else:
            sponsors[int(sponsor.level)] = [sponsor]

    fees = DataGetter.get_fee_settings_by_currency(event.payment_currency)
    code = escape(request.args.get("code"))
    return render_template('gentelella/guest/event/details.html',
                           event=event,
                           sponsors=sponsors,
                           placeholder_images=placeholder_images,
                           custom_placeholder=custom_placeholder,
                           accepted_sessions=accepted_sessions,
                           accepted_sessions_count=len(accepted_sessions),
                           call_for_speakers=call_for_speakers,
                           licence_details=licence_details,
                           speakers=speakers,
                           module=module,
                           timenow_event_tz=timenow_event_tz,
                           current_timezone=get_current_timezone(),
                           tickets=sorted_tickets if sorted_tickets else [],
                           fees=fees,
                           code=code)


@event_detail.route('/<identifier>/sessions/')
def display_event_sessions(identifier):
    event = get_published_event_or_abort(identifier)
    placeholder_images = DataGetter.get_event_default_images()
    if event.sub_topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
    elif event.topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
    else:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')
    if not event.has_session_speakers:
        abort(404)
    call_for_speakers = DataGetter.get_call_for_papers(event.id).first()
    accepted_session_count = get_count(DataGetter.get_sessions(event.id))
    tracks = DataGetter.get_tracks(event.id)
    return render_template('gentelella/guest/event/sessions.html',
                           event=event,
                           placeholder_images=placeholder_images,
                           tracks=tracks,
                           accepted_sessions_count=accepted_session_count,
                           call_for_speakers=call_for_speakers,
                           custom_placeholder=custom_placeholder)


@event_detail.route('/<identifier>/schedule/')
def display_event_schedule(identifier):
    event = get_published_event_or_abort(identifier)
    placeholder_images = DataGetter.get_event_default_images()
    if event.sub_topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
    elif event.topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
    else:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')
    if not event.has_session_speakers:
        abort(404)
    tracks = DataGetter.get_tracks(event.id)
    accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
    call_for_speakers = DataGetter.get_call_for_papers(event.id).first()
    if accepted_sessions_count == 0 or not event.schedule_published_on:
        abort(404)
    return render_template('gentelella/guest/event/schedule.html',
                           event=event,
                           placeholder_images=placeholder_images,
                           accepted_sessions_count=accepted_sessions_count,
                           call_for_speakers=call_for_speakers,
                           tracks=tracks,
                           custom_placeholder=custom_placeholder)


@event_detail.route('/<identifier>/schedule/pentabarf.xml')
def display_event_schedule_pentabarf(identifier):
    event = get_published_event_or_abort(identifier)
    file_url = event.pentabarf_url
    if not event.has_session_speakers:
       abort(404)
    accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
    if accepted_sessions_count == 0 or not event.schedule_published_on:
        abort(404)
    if get_settings()['storage_place'] != "s3" and get_settings()['storage_place'] != 'gs':
        file_url = "file://" + app.config['BASE_DIR'] + file_url.replace("/serve_", "/")
    response = make_response(urlopen(file_url).read())
    response.headers["Content-Type"] = "application/xml"
    return response


@event_detail.route('/<identifier>/schedule/calendar.ics')
def display_event_schedule_ical(identifier):
    event = get_published_event_or_abort(identifier)
    file_url = event.ical_url
    if not event.has_session_speakers:
        abort(404)
    accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
    if accepted_sessions_count == 0 or not event.schedule_published_on:
        abort(404)
    if get_settings()['storage_place'] != "s3" and get_settings()['storage_place'] != 'gs':
        file_url = "file://" + app.config['BASE_DIR'] + file_url.replace("/serve_", "/")
    response = make_response(urlopen(file_url).read())
    response.headers["Content-Type"] = "text/calendar"
    return response


@event_detail.route('/<identifier>/schedule/calendar.xcs')
def display_event_schedule_xcal(identifier):
    event = get_published_event_or_abort(identifier)
    file_url = event.xcal_url
    if not event.has_session_speakers:
        abort(404)
    accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
    if accepted_sessions_count == 0 or not event.schedule_published_on:
        abort(404)
    if get_settings()['storage_place'] != "s3" and get_settings()['storage_place'] != 'gs':
        file_url = "file://" + app.config['BASE_DIR'] + file_url.replace("/serve_", "/")
    response = make_response(urlopen(file_url).read())
    response.headers["Content-Type"] = "application/xml"
    return response


@event_detail.route('/<identifier>/cfs/')
def display_event_cfs(identifier, via_hash=False):
    show_speaker_modal = escape(request.args.get('show_speaker_modal', ''))
    event = get_published_event_or_abort(identifier)
    placeholder_images = DataGetter.get_event_default_images()
    if login.current_user.is_authenticated:
        email = login.current_user.email
        user_speaker = DataGetter.get_speaker_by_email_event(email, event.id)

        existing_sessions = []
        for speaker in user_speaker:
            current_session = []
            for session in speaker.sessions:
                if session.event_id == event.id and not session.deleted_at:
                    if session.title:
                        current_session.append(session)
            if current_session:
                existing_sessions.append(current_session)
    if event.sub_topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
    elif event.topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
    else:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')
    if not event.has_session_speakers:
        abort(404)

    call_for_speakers = DataGetter.get_call_for_papers(event.id).first()

    if not call_for_speakers or (not via_hash and call_for_speakers.privacy == 'private'):
        abort(404)

    form_elems = DataGetter.get_custom_form_elements(event.id)
    speaker_form = json.loads(form_elems.speaker_form)
    session_form = json.loads(form_elems.session_form)

    now = datetime.now(pytz.timezone(event.timezone
                                                  if (event.timezone and event.timezone != '') else 'UTC'))
    start_date = pytz.timezone(event.timezone).localize(call_for_speakers.start_date)
    end_date = pytz.timezone(event.timezone).localize(call_for_speakers.end_date)
    state = "now"
    if end_date < now:
        state = "past"
    elif start_date > now:
        state = "future"
    speakers = DataGetter.get_speakers(event.id).all()
    accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
    if not login.current_user.is_authenticated:
        return render_template('gentelella/guest/event/cfs.html', event=event,
                           speaker_form=speaker_form,
                           accepted_sessions_count=accepted_sessions_count,
                           session_form=session_form,
                           call_for_speakers=call_for_speakers,
                           placeholder_images=placeholder_images,
                           state=state,
                           speakers=speakers,
                           via_hash=via_hash,
                           custom_placeholder=custom_placeholder)
    else:
        return render_template('gentelella/guest/event/cfs.html', event=event,
                           speaker_form=speaker_form,
                           accepted_sessions_count=accepted_sessions_count,
                           session_form=session_form,
                           call_for_speakers=call_for_speakers,
                           placeholder_images=placeholder_images,
                           state=state,
                           speakers=speakers,
                           via_hash=via_hash,
                           custom_placeholder=custom_placeholder,
                           user_speaker=user_speaker,
                           existing_sessions=existing_sessions,
                           show_speaker_modal=show_speaker_modal)


@event_detail.route('/cfs/<hash>/', methods=('GET', 'POST'))
def display_event_cfs_via_hash(hash):
    call_for_speakers = CallForPaper.query.filter_by(hash=hash).first()
    if not call_for_speakers:
        abort(404)
    event = DataGetter.get_event(call_for_speakers.event_id)
    placeholder_images = DataGetter.get_event_default_images()
    if event.sub_topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
    elif event.topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
    else:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')
    if not event.has_session_speakers:
        abort(404)

    if not call_for_speakers:
        abort(404)

    if request.method == 'POST':
        return process_event_cfs(event.identifier)

    form_elems = DataGetter.get_custom_form_elements(event.id)
    speaker_form = json.loads(form_elems.speaker_form)
    session_form = json.loads(form_elems.session_form)

    now = datetime.now(pytz.timezone(event.timezone
                                                  if (event.timezone and event.timezone != '') else 'UTC'))
    start_date = pytz.timezone(event.timezone).localize(call_for_speakers.start_date)
    end_date = pytz.timezone(event.timezone).localize(call_for_speakers.end_date)
    state = "now"
    if end_date < now:
        state = "past"
    elif start_date > now:
        state = "future"
    speakers = DataGetter.get_speakers(event.id).all()
    accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
    return render_template('gentelella/guest/event/cfs.html', event=event,
                           speaker_form=speaker_form,
                           accepted_sessions_count=accepted_sessions_count,
                           session_form=session_form,
                           call_for_speakers=call_for_speakers,
                           placeholder_images=placeholder_images,
                           state=state,
                           speakers=speakers,
                           via_hash=True,
                           custom_placeholder=custom_placeholder)


@event_detail.route('/<identifier>/cfs/new/', methods=('POST', 'GET'))
def process_event_cfs(identifier, via_hash=False):
    if request.method == 'GET':
        event = get_published_event_or_abort(identifier)
        placeholder_images = DataGetter.get_event_default_images()
        if event.sub_topic:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
        elif event.topic:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
        else:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')
        if not event.has_session_speakers:
            abort(404)

        call_for_speakers = DataGetter.get_call_for_papers(event.id).first()

        if not call_for_speakers or (not via_hash and call_for_speakers.privacy == 'private'):
            abort(404)

        form_elems = DataGetter.get_custom_form_elements(event.id)
        speaker_form = json.loads(form_elems.speaker_form)
        session_form = json.loads(form_elems.session_form)

        now = datetime.now(pytz.timezone(event.timezone
                                                  if (event.timezone and event.timezone != '') else 'UTC'))
        start_date = pytz.timezone(event.timezone).localize(call_for_speakers.start_date)
        end_date = pytz.timezone(event.timezone).localize(call_for_speakers.end_date)
        state = "now"
        if end_date < now:
            state = "past"
        elif start_date > now:
            state = "future"
        speakers = DataGetter.get_speakers(event.id).all()
        user_speaker = DataGetter.get_speaker_by_email_event(login.current_user.email, event.id)
        accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
        return render_template('gentelella/guest/event/cfs_new_session.html',
                               event=event,
                               speaker_form=speaker_form,
                               user_speaker=user_speaker,
                               accepted_sessions_count=accepted_sessions_count,
                               session_form=session_form,
                               call_for_speakers=call_for_speakers,
                               placeholder_images=placeholder_images,
                               state=state,
                               speakers=speakers,
                               via_hash=via_hash,
                               custom_placeholder=custom_placeholder,
                               from_path="cfs")

    if request.method == 'POST':
        event = DataGetter.get_event_by_identifier(identifier)
        if not event.has_session_speakers:
            abort(404)
        if login.current_user.is_authenticated:
            DataManager.add_session_to_event(request, event.id, no_name=True)
            flash("Your session proposal has been submitted", "success")
            return redirect(url_for('my_sessions.display_my_sessions_view', event_id=event.id))

        return redirect(url_for('admin.login_view', next=url_for('my_sessions.display_my_sessions_view')))


@event_detail.route('/<identifier>/cfs/new_session/', methods=('POST', 'GET'))
def process_event_cfs_session(identifier, via_hash=False):
    if request.method == 'GET':
        event = get_published_event_or_abort(identifier)
        placeholder_images = DataGetter.get_event_default_images()
        if event.sub_topic:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
        elif event.topic:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
        else:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')
        if not event.has_session_speakers:
            abort(404)

        call_for_speakers = DataGetter.get_call_for_papers(event.id).first()

        if not call_for_speakers or (not via_hash and call_for_speakers.privacy == 'private'):
            abort(404)

        form_elems = DataGetter.get_custom_form_elements(event.id)
        speaker_form = json.loads(form_elems.speaker_form)
        session_form = json.loads(form_elems.session_form)

        now = datetime.now(pytz.timezone(event.timezone
                                                  if (event.timezone and event.timezone != '') else 'UTC'))
        start_date = pytz.timezone(event.timezone).localize(call_for_speakers.start_date)
        end_date = pytz.timezone(event.timezone).localize(call_for_speakers.end_date)
        state = "now"
        if end_date < now:
            state = "past"
        elif start_date > now:
            state = "future"
        speakers = DataGetter.get_speakers(event.id).all()
        user_speaker = DataGetter.get_speaker_by_email_event(login.current_user.email, event.id)
        accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
        return render_template('gentelella/guest/event/cfs_new_session.html',
                               event=event,
                               speaker_form=speaker_form,
                               accepted_sessions_count=accepted_sessions_count,
                               session_form=session_form,
                               call_for_speakers=call_for_speakers,
                               placeholder_images=placeholder_images,
                               state=state,
                               speakers=speakers,
                               user_speaker=user_speaker,
                               via_hash=via_hash,
                               custom_placeholder=custom_placeholder,
                               from_path="cfs")

    if request.method == 'POST':
        email = request.form['email']
        event = DataGetter.get_event_by_identifier(identifier)
        if not event.has_session_speakers:
            abort(404)
        DataManager.add_session_to_event(request, event.id)
        if login.current_user.is_authenticated:
            flash("Your session proposal has been submitted", "success")
            return redirect(url_for('my_sessions.display_my_sessions_view', event_id=event.id))
        else:
            flash(Markup(
                "Your session proposal has been submitted. Please login/register with <strong><u>" + email + "</u></strong> to manage it."),
                "success")
            return redirect(url_for('admin.login_view', next=url_for('my_sessions.display_my_sessions_view')))


@event_detail.route('/<identifier>/cfs/new_speaker/', methods=('POST', 'GET'))
def process_event_cfs_speaker(identifier, via_hash=False):
    if request.method == 'GET':
        event = get_published_event_or_abort(identifier)
        placeholder_images = DataGetter.get_event_default_images()
        if event.sub_topic:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
        elif event.topic:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
        else:
            custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')
        if not event.has_session_speakers:
            abort(404)

        call_for_speakers = DataGetter.get_call_for_papers(event.id).first()

        if not call_for_speakers or (not via_hash and call_for_speakers.privacy == 'private'):
            abort(404)

        form_elems = DataGetter.get_custom_form_elements(event.id)
        speaker_form = json.loads(form_elems.speaker_form)
        session_form = json.loads(form_elems.session_form)

        now = datetime.now(pytz.timezone(event.timezone
                                                  if (event.timezone and event.timezone != '') else 'UTC'))
        start_date = pytz.timezone(event.timezone).localize(call_for_speakers.start_date)
        end_date = pytz.timezone(event.timezone).localize(call_for_speakers.end_date)
        state = "now"
        if end_date < now:
            state = "past"
        elif start_date > now:
            state = "future"
        speakers = DataGetter.get_speakers(event.id).all()
        accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
        return render_template('gentelella/guest/event/cfs_new_speaker.html',
                               event=event,
                               speaker_form=speaker_form,
                               accepted_sessions_count=accepted_sessions_count,
                               session_form=session_form,
                               call_for_speakers=call_for_speakers,
                               placeholder_images=placeholder_images,
                               state=state,
                               speakers=speakers,
                               via_hash=via_hash,
                               custom_placeholder=custom_placeholder,
                               from_path="cfs")

    if request.method == 'POST':
        email = request.form['email']
        event = DataGetter.get_event_by_identifier(identifier)
        if not event.has_session_speakers:
            abort(404)
        DataManager.add_speaker_to_event(request, event.id)
        if login.current_user.is_authenticated:
            flash("You have been registered as Speaker", "success")
            return redirect(url_for('event_detail.display_event_cfs', identifier=identifier, show_speaker_modal=True))
        else:
            flash(Markup(
                "You have been registered as Speaker. Please login/register with <strong><u>" + email + "</u></strong> to manage it."),
                "success")
            return redirect(url_for('admin.login_view', next=url_for('my_sessions.display_my_sessions_view')))


@event_detail.route('/temp/', methods=('POST',))
def add_session_media():
    if 'slides' in request.files and request.files['slides'].filename != '':
        url = DataManager.add_session_media(request, 'slides')
        return jsonify({
            'status': 'ok',
            'url': url
        }), 200

    if 'video' in request.files and request.files['video'].filename != '':
        url = DataManager.add_session_media(request, 'video')
        return jsonify({
            'status': 'ok',
            'url': url
        }), 200

    if 'audio' in request.files and request.files['audio'].filename != '':
        url = DataManager.add_session_media(request, 'audio')
        return jsonify({
            'status': 'ok',
            'url': url
        }), 200

    return jsonify({
            'status': 'ok'
        }), 200


@event_detail.route('/<identifier>/coc/')
def display_event_coc(identifier):
    event = get_published_event_or_abort(identifier)
    placeholder_images = DataGetter.get_event_default_images()
    if event.sub_topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.sub_topic)
    elif event.topic:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name(event.topic)
    else:
        custom_placeholder = DataGetter.get_custom_placeholder_by_name('Other')
    call_for_speakers = DataGetter.get_call_for_papers(event.id).first()
    if not (event.code_of_conduct and event.code_of_conduct != '' and event.code_of_conduct != ' '):
        abort(404)
    accepted_sessions_count = get_count(DataGetter.get_sessions(event.id))
    return render_template('gentelella/guest/event/code_of_conduct.html', event=event,
                           placeholder_images=placeholder_images,
                           accepted_sessions_count=accepted_sessions_count,
                           custom_placeholder=custom_placeholder,
                           call_for_speakers=call_for_speakers)

# SLUGGED PATHS

@event_detail.route('/<identifier>/<slug>/')
def display_event_detail_home_slugged(identifier, slug):
    return display_event_detail_home(identifier)


@event_detail.route('/<identifier>/<slug>/sessions/')
def display_event_sessions_slugged(identifier, slug):
    return display_event_sessions(identifier)
