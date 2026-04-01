"use client";

import { useState } from "react";
import { MOCK_RACES } from "@/lib/mock";
import Link from "next/link";

export default function Home() {
  const dates = [...new Set(MOCK_RACES.map((r) => r.date))];
  const [selectedDate, setSelectedDate] = useState(dates[0]);
  const venues = [...new Set(MOCK_RACES.filter((r) => r.date === selectedDate).map((r) => r.venue))];
  const [selectedVenue, setSelectedVenue] = useState(venues[0]);

  const currentGroup = MOCK_RACES.find(
    (r) => r.date === selectedDate && r.venue === selectedVenue
  );

  function handleDateChange(date: string) {
    setSelectedDate(date);
    const newVenues = [...new Set(MOCK_RACES.filter((r) => r.date === date).map((r) => r.venue))];
    if (!newVenues.includes(selectedVenue)) {
      setSelectedVenue(newVenues[0]);
    }
  }

  const dayLabel = (d: string) => {
    const dt = new Date(d);
    const days = ["日", "月", "火", "水", "木", "金", "土"];
    return `${dt.getMonth() + 1}/${dt.getDate()}(${days[dt.getDay()]})`;
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-xl font-bold mb-4">JRA レース一覧</h1>

      {/* Date tabs */}
      <div className="flex gap-2 mb-3">
        {dates.map((d) => (
          <button
            key={d}
            onClick={() => handleDateChange(d)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border transition ${
              selectedDate === d
                ? "bg-[#E53935] text-white border-[#E53935]"
                : "bg-white text-[#555] border-[#ddd] hover:bg-[#f5f5f5]"
            }`}
          >
            {dayLabel(d)}
          </button>
        ))}
      </div>

      {/* Venue tabs */}
      <div className="flex gap-2 mb-5">
        {venues.map((v) => (
          <button
            key={v}
            onClick={() => setSelectedVenue(v)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border transition ${
              selectedVenue === v
                ? "bg-[#333] text-white border-[#333]"
                : "bg-white text-[#555] border-[#ddd] hover:bg-[#f5f5f5]"
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {/* Race list */}
      {currentGroup ? (
        <div className="grid gap-2">
          {currentGroup.races.map((race) => (
            <Link
              key={race.race_id}
              href={`/race/${encodeURIComponent(race.race_id)}`}
              className="flex items-center gap-3 px-4 py-3 rounded-lg border border-[#e0e0e0] hover:bg-[#fafafa] transition"
            >
              <span className="text-sm font-bold text-[#E53935] w-8 shrink-0">
                {race.race_number}R
              </span>
              <span className="text-sm text-[#888] w-12 shrink-0">{race.start_time}</span>
              <span className="text-sm font-medium flex-1 truncate">{race.race_name}</span>
              <span className="text-xs text-[#888]">{race.distance}</span>
              <span className="text-xs text-[#aaa]">{race.headcount}頭</span>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-[#888] text-sm">レースデータがありません</p>
      )}
    </div>
  );
}
