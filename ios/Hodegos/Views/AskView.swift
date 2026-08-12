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
            .hodScreen()
            .navigationTitle("Ask Nikos")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if !messages.isEmpty {
                        Button {
                            messages = []
                            input = ""
                        } label: {
                            Image(systemName: "square.and.pencil")
                                .foregroundStyle(Color.hodAegean)
                        }
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    if let name = location.placeName {
                        Label(name, systemImage: "location.fill")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(Color.hodAegean)
                    }
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 14) {
            Spacer()
            Text("🏛️").font(.system(size: 44))
            Text("Ask me anything out here")
                .font(.hodDisplay(.title2))
            Text("History, food, transit, hours — I know where you're standing and what's on your itinerary.")
                .font(.footnote).foregroundStyle(Color.hodMuted)
                .multilineTextAlignment(.center).padding(.horizontal, 40)
            ForEach(starters, id: \.self) { q in
                Button(q) { send(q) }
                    .buttonStyle(.bordered)
                    .font(.subheadline)
                    .tint(.hodAegean)
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
                            selectedTab = 3 // Map tab
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
            .tint(.hodAegean)
            Text(memoryMode
                 ? "Answers come from your trip archive"
                 : "Ask about anything on this trip")
                .font(.caption2).foregroundStyle(Color.hodMuted)
            Spacer()
        }
        .padding(.horizontal)
        .padding(.top, 6)
    }

    private var inputBar: some View {
        HStack(spacing: 8) {
            TextField(memoryMode ? "Ask about your trip so far…" : "Ask Nikos…", text: $input, axis: .vertical)
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
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
                    .foregroundStyle(Color.hodAegean)
            }
            .disabled(input.trimmingCharacters(in: .whitespaces).isEmpty || isThinking)
        }
        .padding()
        .background(Color.hodPaper)
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
                    memoryMode: memoryMode,
                    timestamp: ISO8601DateFormatter().string(from: Date())
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
