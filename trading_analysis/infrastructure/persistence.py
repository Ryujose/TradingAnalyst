from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from ..domain.interfaces import RunnersPersistence, NewsRepository
from ..domain.models import RunnerItem, RunnerSnapshot, NewsItem, RunnerNewsLink

Base = declarative_base()

class RunnerSnapshotDB(Base):
    __tablename__ = 'runner_snapshots'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    universe_size = Column(Integer)
    runners = relationship("RunnerItemDB", back_populates="snapshot")

class RunnerItemDB(Base):
    __tablename__ = 'runner_items'
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('runner_snapshots.id'))
    ticker = Column(String(10))
    price = Column(Float)
    change = Column(Float)
    pct_change = Column(Float)
    volume = Column(Integer)
    relative_volume = Column(Float)
    gap_pct = Column(Float)
    vwap_dist = Column(Float)
    volatility = Column(Float)
    range_expansion = Column(Float)
    volume_acceleration = Column(Float)
    market_cap = Column(Float)
    float_size = Column(Float)
    score = Column(Float)
    classification = Column(String(50))
    timestamp = Column(DateTime)
    
    snapshot = relationship("RunnerSnapshotDB", back_populates="runners")

class NewsDB(Base):
    __tablename__ = 'news'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), index=True)
    title = Column(String(255))
    content = Column(Text)
    publisher = Column(String(100))
    link = Column(String(500))
    news_type = Column(String(50), index=True)
    sentiment = Column(String(20), index=True)
    catalyst_strength = Column(Integer)
    provider_publish_time = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

class RunnerNewsLinkDB(Base):
    __tablename__ = 'runner_news_links'
    id = Column(Integer, primary_key=True)
    runner_id = Column(String(50), index=True) # e.g. 20250218-TSLA
    news_id = Column(Integer, ForeignKey('news.id'), index=True)
    linked_at = Column(DateTime, default=datetime.now)

class SQLAlchemyRunnersPersistence(RunnersPersistence):
    def __init__(self, database_url: str = "sqlite:///runners.db"):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_snapshot(self, snapshot: RunnerSnapshot):
        session = self.Session()
        try:
            db_snapshot = RunnerSnapshotDB(
                timestamp=snapshot.timestamp,
                universe_size=snapshot.universe_size
            )
            session.add(db_snapshot)
            session.flush() # To get the id
            
            for item in snapshot.runners:
                db_item = RunnerItemDB(
                    snapshot_id=db_snapshot.id,
                    ticker=item.ticker,
                    price=item.price,
                    change=item.change,
                    pct_change=item.pct_change,
                    volume=item.volume,
                    relative_volume=item.relative_volume,
                    gap_pct=item.gap_pct,
                    vwap_dist=item.vwap_dist,
                    volatility=item.volatility,
                    range_expansion=item.range_expansion,
                    volume_acceleration=item.volume_acceleration,
                    market_cap=item.market_cap,
                    float_size=item.float_size,
                    score=item.score,
                    classification=item.classification,
                    timestamp=item.timestamp
                )
                session.add(db_item)
            
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_history(self, ticker: Optional[str] = None, start_date: Optional[datetime] = None) -> List[RunnerItem]:
        session = self.Session()
        try:
            query = session.query(RunnerItemDB)
            if ticker:
                query = query.filter(RunnerItemDB.ticker == ticker)
            if start_date:
                query = query.filter(RunnerItemDB.timestamp >= start_date)
            
            db_items = query.order_by(RunnerItemDB.timestamp.desc()).all()
            
            return [
                RunnerItem(
                    ticker=db_item.ticker,
                    price=db_item.price,
                    change=db_item.change,
                    pct_change=db_item.pct_change,
                    volume=db_item.volume,
                    relative_volume=db_item.relative_volume,
                    gap_pct=db_item.gap_pct,
                    vwap_dist=db_item.vwap_dist,
                    volatility=db_item.volatility,
                    range_expansion=db_item.range_expansion,
                    volume_acceleration=db_item.volume_acceleration,
                    market_cap=db_item.market_cap,
                    float_size=db_item.float_size,
                    score=db_item.score,
                    classification=db_item.classification,
                    timestamp=db_item.timestamp
                )
                for db_item in db_items
            ]
        finally:
            session.close()

class SQLAlchemyNewsRepository(NewsRepository):
    def __init__(self, database_url: str = "sqlite:///runners.db"):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add(self, news: NewsItem) -> NewsItem:
        session = self.Session()
        try:
            db_news = NewsDB(
                symbol=news.symbol,
                title=news.title,
                content=news.content,
                publisher=news.publisher,
                link=news.link,
                news_type=news.news_type.value if hasattr(news.news_type, 'value') else news.news_type,
                sentiment=news.sentiment.value if hasattr(news.sentiment, 'value') else news.sentiment,
                catalyst_strength=news.catalyst_strength,
                provider_publish_time=news.provider_publish_time,
                created_at=news.created_at,
                updated_at=news.updated_at,
                is_active=news.is_active
            )
            session.add(db_news)
            session.commit()
            session.refresh(db_news)
            news.id = db_news.id
            return news
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, news_id: int, updates: dict) -> NewsItem:
        session = self.Session()
        try:
            db_news = session.query(NewsDB).filter(NewsDB.id == news_id).first()
            if not db_news:
                raise ValueError(f"News with id {news_id} not found")
            
            for key, value in updates.items():
                if hasattr(db_news, key):
                    if key in ['news_type', 'sentiment'] and hasattr(value, 'value'):
                        setattr(db_news, key, value.value)
                    else:
                        setattr(db_news, key, value)
            
            db_news.updated_at = datetime.now()
            session.commit()
            session.refresh(db_news)
            return self._map_to_domain(db_news)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, news_id: int, soft: bool = True):
        session = self.Session()
        try:
            db_news = session.query(NewsDB).filter(NewsDB.id == news_id).first()
            if db_news:
                if soft:
                    db_news.is_active = False
                else:
                    session.delete(db_news)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, news_id: int) -> Optional[NewsItem]:
        session = self.Session()
        try:
            db_news = session.query(NewsDB).filter(NewsDB.id == news_id).first()
            if db_news:
                return self._map_to_domain(db_news)
            return None
        finally:
            session.close()

    def list(self, symbol: Optional[str] = None, news_type: Optional[str] = None, 
             sentiment: Optional[str] = None, limit: int = 50) -> List[NewsItem]:
        session = self.Session()
        try:
            query = session.query(NewsDB).filter(NewsDB.is_active == True)
            if symbol:
                query = query.filter(NewsDB.symbol == symbol.upper())
            if news_type:
                query = query.filter(NewsDB.news_type == news_type)
            if sentiment:
                query = query.filter(NewsDB.sentiment == sentiment)
            
            db_news_list = query.order_by(NewsDB.provider_publish_time.desc()).limit(limit).all()
            return [self._map_to_domain(db_news) for db_news in db_news_list]
        finally:
            session.close()

    def search(self, keyword: str) -> List[NewsItem]:
        session = self.Session()
        try:
            query = session.query(NewsDB).filter(
                NewsDB.is_active == True,
                (NewsDB.title.ilike(f"%{keyword}%") | NewsDB.content.ilike(f"%{keyword}%"))
            )
            db_news_list = query.order_by(NewsDB.provider_publish_time.desc()).all()
            return [self._map_to_domain(db_news) for db_news in db_news_list]
        finally:
            session.close()

    def link_to_runner(self, runner_id: str, news_id: int) -> RunnerNewsLink:
        session = self.Session()
        try:
            db_link = RunnerNewsLinkDB(runner_id=runner_id, news_id=news_id)
            session.add(db_link)
            session.commit()
            session.refresh(db_link)
            return RunnerNewsLink(
                id=db_link.id,
                runner_id=db_link.runner_id,
                news_id=db_link.news_id,
                linked_at=db_link.linked_at
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def unlink_from_runner(self, runner_id: str, news_id: int):
        session = self.Session()
        try:
            db_link = session.query(RunnerNewsLinkDB).filter(
                RunnerNewsLinkDB.runner_id == runner_id,
                RunnerNewsLinkDB.news_id == news_id
            ).first()
            if db_link:
                session.delete(db_link)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_links_for_runner(self, runner_id: str) -> List[RunnerNewsLink]:
        session = self.Session()
        try:
            db_links = session.query(RunnerNewsLinkDB).filter(RunnerNewsLinkDB.runner_id == runner_id).all()
            return [
                RunnerNewsLink(
                    id=db_link.id,
                    runner_id=db_link.runner_id,
                    news_id=db_link.news_id,
                    linked_at=db_link.linked_at
                ) for db_link in db_links
            ]
        finally:
            session.close()

    def get_news_for_runner(self, runner_id: str) -> List[NewsItem]:
        session = self.Session()
        try:
            db_news_list = session.query(NewsDB).join(
                RunnerNewsLinkDB, NewsDB.id == RunnerNewsLinkDB.news_id
            ).filter(RunnerNewsLinkDB.runner_id == runner_id).all()
            return [self._map_to_domain(db_news) for db_news in db_news_list]
        finally:
            session.close()

    def _map_to_domain(self, db_news: NewsDB) -> NewsItem:
        return NewsItem(
            id=db_news.id,
            symbol=db_news.symbol,
            title=db_news.title,
            content=db_news.content,
            publisher=db_news.publisher,
            link=db_news.link,
            news_type=db_news.news_type,
            sentiment=db_news.sentiment,
            catalyst_strength=db_news.catalyst_strength,
            provider_publish_time=db_news.provider_publish_time,
            created_at=db_news.created_at,
            updated_at=db_news.updated_at,
            is_active=db_news.is_active
        )
