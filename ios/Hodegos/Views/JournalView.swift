import CoreLocation
import SwiftUI

struct JournalView: View {
    @EnvironmentObject var location: LocationManager

    @State private var entryId: String?
    @State private var messages: [ChatMessage] = []
    @State private var candidate: Place?
    @State private var confirmedPlace: String?
    @State private var mapsLink = ""
    @State private var input = ""
    @State private var isThinking = false
    @State private var saved = false
    @State private var showNewEntryAlert = false
    @FocusState private var inputFocused: Bool

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if let confirmedPlace {
                    HStack(spacing: 8) {
                        Image(systemName: "mappin.circle.fill").foregroundStyle(Color.hodTerra)
                        Text(confirmedPlace)
                            .font(.hodDisplay(.headline))
                            .foregroundStyle(Color.hodTerra)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal).padding(.vertical, 6)
                    .background(Color.hodTerra.opacity(0.12))
                }
                if entryId == nil {
                    linkField
                }
                thread
                inputBar
            }
            .hodScreen(tint: .hodTerra)
            .navigationTitle("Journal")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if !messages.isEmpty {
                        Button { showNewEntryAlert = true } label: {
                            Image(systemName: "square.and.pencil")
                                .foregroundStyle(Color.hodTerra)
                        }
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { finish() }
                        .fontWeight(.semibold)
                        .disabled(entryId == nil || isThinking)
                }
            }
            .alert("Saved to your Journey ✓", isPresented: $saved) {
                Button("OK") {}
            }
            .alert("Start a new entry?", isPresented: $showNewEntryAlert) {
                if entryId != nil {
                    Button("Save & Start New") { finish() }
                }
                Button("Discard", role: .destructive) { resetState() }
                Button("Cancel", role: .cancel) {}
            }
        }
    }

    private var linkField: some View {
        TextField("Paste a Google Maps link (optional)", text: $mapsLink)
            .textFieldStyle(.roundedBorder)
            .font(.footnote)
            .padding(.horizontal).padding(.top, 8)
    }

    private var thread: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    if messages.isEmpty {
                        Text("How was it? Tell me about somewhere you just went — a meal, a monastery, a museum, anything. 🎙️")
                            .padding(12)
                            .background(Color.hodCard)
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.hodInk.opacity(0.08)))
                    }
                    ForEach(messages) { msg in
                        MessageBubble(message: msg, onShowMap: { _ in }, accent: .hodTerra)
                            .id(msg.id)
                    }
                    if let candidate {
                        CandidateCard(place: candidate,
                                      onYes: { confirm(true) },
                                      onNo: { confirm(false) })
                    }
                    if isThinking { ProgressView().padding(.leading, 16) }
                }
                .padding()
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: messages.count) {
                if let last = messages.last { proxy.scrollTo(last.id, anchor: .bottom) }
            }
        }
    }

    private var inputBar: some View {
        HStack(spacing: 8) {
            TextField("Tell Nikos more about it…", text: $input, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .focused($inputFocused)
                .onSubmit { send() }
                .toolbar {
                    ToolbarItemGroup(placement: .keyboard) {
                        Spacer()
                        Button("Done") { inputFocused = false }
                    }
                }
            Button { send() } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
                    .foregroundStyle(Color.hodTerra)
            }
            .disabled(input.trimmingCharacters(in: .whitespaces).isEmpty || isThinking || candidate != nil)
        }
        .padding()
        .background(Color.hodPaper)
    }

    private func send() {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        messages.append(ChatMessage(role: .user, text: text))
        input = ""
        isThinking = true
        Task {
            defer { isThinking = false }
            do {
                if entryId == nil {
                    let started = try await APIClient.shared.journalStart(
                        mapsLink: mapsLink.isEmpty ? nil : mapsLink)
                    entryId = started.entryId
                }
                let response = try await APIClient.shared.journalMessage(
                    entryId: entryId!, message: text,
                    lat: location.coordinate?.latitude,
                    lon: location.coordinate?.longitude)
                messages.append(ChatMessage(role: .niko, text: response.reply))
                candidate = response.candidate
            } catch {
                messages.append(ChatMessage(role: .niko, text: error.localizedDescription))
            }
        }
    }

    private func confirm(_ accepted: Bool) {
        guard let entryId else { return }
        let name = candidate?.name
        candidate = nil
        isThinking = true
        Task {
            defer { isThinking = false }
            do {
                let response = try await APIClient.shared.journalConfirm(entryId: entryId, accepted: accepted)
                if accepted { confirmedPlace = name }
                messages.append(ChatMessage(role: .niko, text: response.reply))
            } catch {
                messages.append(ChatMessage(role: .niko, text: error.localizedDescription))
            }
        }
    }

    private func resetState() {
        entryId = nil
        messages = []
        confirmedPlace = nil
        candidate = nil
        mapsLink = ""
        input = ""
    }

    private func finish() {
        guard let id = entryId else { return }
        isThinking = true
        Task {
            defer { isThinking = false }
            do {
                _ = try await APIClient.shared.journalFinish(entryId: id)
                entryId = nil
                messages = []
                confirmedPlace = nil
                mapsLink = ""
                saved = true
            } catch {
                messages.append(ChatMessage(role: .niko, text: error.localizedDescription))
            }
        }
    }
}
