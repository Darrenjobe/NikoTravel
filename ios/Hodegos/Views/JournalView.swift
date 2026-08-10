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

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if let confirmedPlace {
                    Label(confirmedPlace, systemImage: "mappin.circle.fill")
                        .font(.footnote.weight(.semibold))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal).padding(.vertical, 6)
                        .background(.orange.opacity(0.12))
                }
                if entryId == nil {
                    linkField
                }
                thread
                inputBar
            }
            .navigationTitle("Journal")
            .navigationBarTitleDisplayMode(.inline)
            .tint(.orange)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { finish() }
                        .fontWeight(.semibold)
                        .disabled(entryId == nil || isThinking)
                }
            }
            .alert("Saved to your Journey ✓", isPresented: $saved) {
                Button("OK") {}
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
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 10) {
                if messages.isEmpty {
                    Text("How was it? Tell me about somewhere you just went — a meal, a monastery, a museum, anything. 🎙️")
                        .padding(12)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                }
                ForEach(messages) { msg in
                    MessageBubble(message: msg, onShowMap: { _ in })
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
    }

    private var inputBar: some View {
        HStack(spacing: 8) {
            TextField("Tell Niko about it…", text: $input, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .onSubmit { send() }
            Button {
                send()
            } label: {
                Image(systemName: "arrow.up.circle.fill").font(.title2)
            }
            .disabled(input.trimmingCharacters(in: .whitespaces).isEmpty || isThinking || candidate != nil)
        }
        .padding()
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

struct CandidateCard: View {
    let place: Place
    let onYes: () -> Void
    let onNo: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "mappin.circle.fill").font(.title2).foregroundStyle(.orange)
                VStack(alignment: .leading) {
                    Text(place.name ?? "Unknown").font(.subheadline.weight(.bold))
                    Text(place.address ?? "").font(.caption).foregroundStyle(.secondary)
                }
            }
            Text("Is this the place?").font(.footnote)
            HStack {
                Button("Yes, that's it", action: onYes)
                    .buttonStyle(.borderedProminent).tint(.orange)
                Button("No", action: onNo)
                    .buttonStyle(.bordered)
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}
