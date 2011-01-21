#!/usr/bin/env ruby

require 'iplayer'
include IPlayer

if ARGV.length < 1
  puts 'Usage: iplayer-dl-subtitles pid'
  exit 1
end

pid = ARGV[0]
http = Net::HTTP
browser = Browser.new(http)
pid = Downloader.extract_pid(pid)
downloader = Downloader.new(browser, pid)
version_pid = downloader.available_versions.first.pid
subtitles = Subtitles.new(version_pid, browser)
xml = subtitles.w3c_timed_text

if xml.nil?
  puts "No subtitles found for version %s" % version_pid
  exit 1
end

puts xml

