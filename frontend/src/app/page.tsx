"use client";

import { useState, useEffect } from "react";
import { fetchRaces, getAvailableDates } from "@/lib/api";
import type { RaceSummary } from "@/lib/types";
import Link from "next/link";

function dateLabel(d: string): string {
  const dt = new Date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`);
  const days = ["日", "月", "火", "水", "木", "金", "土"];
  return `${dt.getMonth() + 1}/${dt.getDate()}(${days[dt.getDay()]})`;
}

export default function Home() {
  const mockDates = getAvailableDates();
  const dates = mockDates.length > 0 ? mockDates : ["20260329"];
  const [selectedDate, setSelectedDate] = useState(dates[0]);
  const [venues, setVenues] = useState<{ venue: string; races: RaceSummary[] }[]>([]);
  const [selectedVenue, setSelectedVenue] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchRaces(selectedDate).then((data) => {
      setVenues(data.venues);
      if (data.venues.length > 0) {
        setSelectedVenue((prev) =>
          data.venues.find((v) => v.venue === prev) ? prev : data.venues[0].venue
        );
      } else {
        setSelectedVenue("");
      }
      setLoading(false);
    });
  }, [selectedDate]);

  const currentRaces = venues.find((v) => v.venue === selectedVenue)?.races || [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-xl font-bold mb-4">JRA レース一覧</h1>

      {/* Date tabs */}
      <div className="flex gap-2 mb-3">
        {dates.map((d) => (
          <button
            key={d}
            onClick={() => setSelectedDate(d)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border transition ${
              selectedDate === d
                ? "bg-[#E53935] text-white border-[#E53935]"
                : "bg-white text-[#555] border-[#ddd] hover:bg-[#f5f5f5]"
            }`}
          >
            {dateLabel(d)}
          </button>
        ))}
      </div>

      {/* Venue tabs */}
      {venues.length > 0 && (
        <div className="flex gap-2 mb-5">
          {venues.map((v) => (
            <button
              key={v.venue}
              onClick={() => setSelectedVenue(v.venue)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium border transition ${
                selectedVenue === v.venue
                  ? "bg-[#333] text-white border-[#333]"
                  : "bg-white text-[#555] border-[#ddd] hover:bg-[#f5f5f5]"
              }`}
            >
              {v.venue}
              <span className="ml-1 text-xs opacity-70">{v.races.length}R</span>
            </button>
          ))}
        </div>
      )}

      {/* Race list */}
      {loading ? (
        <p className="text-[#888] text-sm py-8 text-center">読み込み中...</p>
      ) : currentRaces.length > 0 ? (
        <div className="grid gap-2">
          {currentRaces.map((race) => (
            <Link
              key={race.race_id}
              href={`/race/${encodeURIComponent(race.race_id)}`}
              className="flex items-center gap-3 px-4 py-3 rounded-lg border border-[#e0e0e0] hover:bg-[#fafafa] transition"
            >
              <span className="text-sm font-bold text-[#E53935] w-8 shrink-0">
                {race.race_number}R
              </span>
              {race.start_time && (
                <span className="text-sm text-[#888] w-12 shrink-0">{race.start_time}</span>
              )}
              <span className="text-sm font-medium flex-1 truncate">{race.race_name}</span>
              <span className="text-xs text-[#888]">{race.distance}</span>
              <span className="text-xs text-[#aaa]">{race.headcount}頭</span>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-[#888] text-sm py-8 text-center">この日のレースデータはまだありません</p>
      )}
    </div>
  );
}
