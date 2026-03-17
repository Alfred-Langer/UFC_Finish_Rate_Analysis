# db/loader.py
import logging
from sqlalchemy.exc import IntegrityError
from models.fighter import Fighter
from models.bout import Bout
from models.event import Event

logger = logging.getLogger(__name__)


def load_fighters(session, fighters):
    for fighter in fighters:
        existing = session.query(Fighter).filter(
            Fighter.name == fighter.name,
            Fighter.tapology_id == fighter.tapology_id
            ).first()

        if existing:
            existing.age = fighter.age
            existing.number_of_total_bouts = fighter.number_of_total_bouts
            existing.wins = fighter.wins
            existing.losses = fighter.losses
            existing.draws = fighter.draws
            existing.no_contests = fighter.no_contests
            existing.overall_finish_rate = fighter.overall_finish_rate
            existing.nick_name = fighter.nick_name
            existing.sex = fighter.sex  # Probably not going to change but you never know.
            existing.tapology_id = fighter.tapology_id # In case Tapology changes it for some reason
            existing.height = fighter.height
            existing.reach = fighter.reach
            existing.latest_bout_date = fighter.latest_bout_date
            existing.date_of_death = fighter.date_of_death

            # TODO: Add logic to update fighter's former nicknames if they have changed

        else:
            session.add(fighter)

    session.flush()
    logger.info(f"Loaded {len(fighters)} fighters")


def load_bouts(session, bouts):
    for bout in bouts:
        existing = session.query(Bout).filter(
            Bout.event_id == bout.event_id,
            Bout.fighter_one == bout.fighter_one,
            Bout.fighter_two == bout.fighter_two
        ).first()

        if existing:
            existing.method_of_victory = bout.method_of_victory
            existing.winner = bout.winner
            existing.finish = bout.finish
            existing.finish_rate_at_bout = bout.finish_rate_at_bout
            existing.fighter_one_age_at_bout = bout.fighter_one_age_at_bout
            existing.fighter_two_age_at_bout = bout.fighter_two_age_at_bout
        else:
            session.add(bout)

    session.flush()
    logger.info(f"Loaded {len(bouts)} bouts")

def load_events(session, events):
    seen_titles = set()
    for event in events:
        if event.title in seen_titles:
            logger.warning(f"Duplicate event title in parsed batch: '{event.title}' — skipping")
            continue
        existing = session.query(Event).filter_by(title=event.title).first()
        if existing:
            existing.country = event.country
            existing.state = event.state
            existing.date = event.date
            existing.time = event.time
            session.flush()  # ensure existing.id is available before upserting bouts
            for bout in event.bouts:
                bout_existing = session.query(Bout).filter(
                    Bout.event_id == existing.id,
                    Bout.fighter_one == bout.fighter_one,
                    Bout.fighter_two == bout.fighter_two,
                ).first()
                if bout_existing:
                    bout_existing.method_of_victory = bout.method_of_victory
                    bout_existing.winner = bout.winner
                    bout_existing.finish = bout.finish
                    bout_existing.fighter_one_age_at_bout = bout.fighter_one_age_at_bout
                    bout_existing.fighter_two_age_at_bout = bout.fighter_two_age_at_bout
                else:
                    bout.event_id = existing.id
                    session.add(bout)
        else:
            sp = session.begin_nested()
            try:
                session.add(event)  # cascades to event.bouts; event_id set automatically on flush
                sp.commit()
            except IntegrityError:
                sp.rollback()
                logger.warning(f"Event '{event.title}' already exists in DB (missed by title lookup) — skipping")
        seen_titles.add(event.title)
    session.flush()
    logger.info(f"Loaded {len(events)} events")
