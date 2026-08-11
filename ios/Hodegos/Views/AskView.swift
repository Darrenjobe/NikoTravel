import CoreLocation
import SwiftUI

struct AskView: View {
    @EnvironmentObject var location: LocationManager
    @Binding var recommendedPlaces: [Place]
    @Binding var selectedTab: Int

    @State private var messages: [ChatMessage] = []
    @State private var input = ""
    @State private var memoryMode = false
    @State private var isThinking = false
    @FocusState private var inputFocused: Bool

    private let starters = [
        "What happened at the Areopagus?",
        "Where should I eat nearby?",
        "Is the Acropolis open right now?",
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if messages.isEmpty {
                    emptyState
                } else {
                    thread
                }
                memoryBar
                inputBar
            }
            .navigationTitle("Ask Niko")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    if let name = location.placeName {
                        Label(name, systemImage: "location.fill")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.tint)
                    }
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 14) {
            Spacer()
            Text("🏛️").font(.system(size: 44))
            Text("Ask me anything out here").font(.headline)
            Text("History, food, transit, hours — I know where you're standing and what's on your itinerary.")
                .font(.footnote).foregroundStyle(.secondary)
                .multilineTextAlignment(.center).padding(.horizontal, 40)
            ForEach(starters, id: \.self) { q in
                Button(q) { send(q) }
                    .buttonStyle(.bordered)
                    .font(.subheadline)
            }
            Spacer()
        }
    }

    private var thread: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(messages) { msg in
                        MessageBubble(message: msg) { places in
                            recommendedPlaces = places
                            selectedTab = 2 // Map tab
                        }
                        .id(msg.id)
                    }
                    if isThinking {
                        ProgressView().padding(.leading, 16)
                    }
                }
                .padding()
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: messages.count) {
                if let last = messages.last { proxy.scrollTo(last.id, anchor: .bottom) }
            }
        }
    }

    private var memoryBar: some View {
        HStack {
            Toggle(isOn: $memoryMode) {
                Label("Trip memory", systemImage: "book.closed")
                    .font(.caption.weight(.semibold))
            }
            .toggleStyle(.button)
            .tint(.blue)
            Text(memoryMode
                 ? "Answers come from your trip archive"
                 : "Ask about anything on this trip")
                .font(.caption2).foregroundStyle(.secondary)
            Spacer()
        }
        .padding(.horizontal)
        .padding(.top, 6)
    }

    private var inputBar: some View {
        HStack(spacing: 8) {
            // The keyboard's built-in mic button provides dictation — no
            // custom speech code needed for V1.
            TextField(memoryMode ? "Ask about your trip so far…" : "Ask Niko…", text: $input, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .focused($inputFocused)
                .onSubmit { send(input) }
                .toolbar {
                    ToolbarItemGroup(placement: .keyboard) {
                        Spacer()
                        Button("Done") { inputFocused = false }
                    }
                }
            Button {
                send(input)
            } label: {
                Image(systemName: "arrow.up.circle.fill").font(.title2)
            }
            .disabled(input.trimmingCharacters(in: .whitespaces).isEmpty || isThinking)
        }
        .padding()
    }

    private func send(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        messages.append(ChatMessage(role: .user, text: trimmed))
        input = ""
        isThinking = true
        Task {
            defer { isThinking = false }
            do {
                let response = try await APIClient.shared.chat(ChatRequest(
                    message: trimmed,
                    lat: location.coordinate?.latitude,
                    lon: location.coordinate?.longitude,
                    memoryMode: memoryMode
                ))
                messages.append(ChatMessage(
                    role: .niko, text: response.reply,
                    places: response.places,
                    sources: response.sources.compactMap { $0 }
                ))
            } catch {
                messages.append(ChatMessage(role: .niko, text: error.localizedDescription))
            }
        }
    }
}

struct MessageBubble: View {
    let message: ChatMessage
    let onShowMap: ([Place]) -> Void

    var body: some View {
        VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 6) {
            Text(message.text)
                .padding(12)
                .background(message.role == .user ? Color.blue : Color(.secondarySystemBackground))
                .foregroundStyle(message.role == .user ? .white : .primary)
                .clipShape(RoundedRectangle(cornerRadius: 16))
            if !message.places.isEmpty {
                Button {
                    onShowMap(message.places)
                } label: {
                    Label("Show these on the map", systemImage: "mappin.and.ellipse")
                        .font(.subheadline.weight(.semibold))
                }
                .buttonStyle(.borderedProminent)
            }
            if !message.sources.isEmpty {
                Text("📓 " + message.sources.joined(separator: " · "))
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.blue)
            }
        }
        .frame(maxWidth: .infinity, alignment: message.role == .user ? .trailing : .leading)
    }
}
